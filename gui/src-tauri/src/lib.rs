use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};
use serde::Serialize;
use serde_json::{Value, json};
use std::fs;
use std::path::Path;
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};

const CREATE_NO_WINDOW: u32 = 0x0800_0000;
const THUMBNAIL_MAX_BYTES: usize = 2 * 1024 * 1024;
static TEMP_SEQUENCE: AtomicU64 = AtomicU64::new(0);

#[derive(Debug, Serialize)]
struct SproutCliError {
    code: String,
    message: String,
    details: Value,
}

impl SproutCliError {
    fn new(code: impl Into<String>, message: impl Into<String>, details: Value) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
            details,
        }
    }
}

fn command_arguments(args: &[String]) -> Vec<String> {
    let mut result = args.to_vec();
    if !result.iter().any(|argument| argument == "--json") {
        result.push("--json".to_owned());
    }
    result
}

fn parse_cli_error(stderr: &str, exit_code: Option<i32>) -> SproutCliError {
    if let Ok(mut payload) = serde_json::from_str::<Value>(stderr.trim()) {
        if let Some(object) = payload.as_object_mut() {
            let code = object
                .remove("code")
                .and_then(|value| value.as_str().map(str::to_owned));
            let message = object
                .remove("message")
                .and_then(|value| value.as_str().map(str::to_owned));
            let mut details = object.remove("details").unwrap_or_else(|| json!({}));
            if let Some(details_object) = details.as_object_mut() {
                details_object.insert("exit_code".to_owned(), json!(exit_code));
            }
            if let (Some(code), Some(message)) = (code, message) {
                return SproutCliError::new(code, message, details);
            }
        }
    }

    let message = stderr.trim();
    SproutCliError::new(
        "sprout_cli_failed",
        if message.is_empty() {
            "Sprout CLIがエラー終了しました".to_owned()
        } else {
            message.to_owned()
        },
        json!({ "exit_code": exit_code }),
    )
}

#[tauri::command]
fn run_sprout(
    project_dir: String,
    args: Vec<String>,
    sprout_program: Option<String>,
) -> Result<Value, SproutCliError> {
    if args.is_empty() {
        return Err(SproutCliError::new(
            "invalid_request",
            "Sproutのコマンドが指定されていません",
            json!({}),
        ));
    }

    let project = Path::new(&project_dir);
    if !project.is_dir() {
        return Err(SproutCliError::new(
            "project_not_found",
            "選択したプロジェクトフォルダが見つかりません",
            json!({ "project_dir": project_dir }),
        ));
    }

    // Keep executable resolution behind one value so a bundled sidecar can replace PATH later.
    let program = sprout_program
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .unwrap_or("sprout");
    let arguments = command_arguments(&args);
    let mut command = Command::new(program);
    command
        .current_dir(project)
        .args(arguments)
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8")
        .env("NO_COLOR", "1");

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    let output = command.output().map_err(|error| {
        let code = if error.kind() == std::io::ErrorKind::NotFound {
            "sprout_not_found"
        } else {
            "sprout_spawn_failed"
        };
        SproutCliError::new(
            code,
            if code == "sprout_not_found" {
                "Sprout CLIが見つかりません。PATHまたはCLIパス設定を確認してください"
            } else {
                "Sprout CLIを起動できませんでした"
            },
            json!({ "program": program, "reason": error.to_string() }),
        )
    })?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    if !output.status.success() {
        return Err(parse_cli_error(&stderr, output.status.code()));
    }

    serde_json::from_str(stdout.trim()).map_err(|error| {
        SproutCliError::new(
            "invalid_json_output",
            "Sprout CLIから有効なJSONが返されませんでした",
            json!({ "reason": error.to_string(), "stdout": stdout.trim() }),
        )
    })
}

fn thumbnail_data_url(media_type: &str, bytes: &[u8]) -> Result<String, SproutCliError> {
    if !matches!(media_type, "image/png" | "image/jpeg" | "image/webp") {
        return Err(SproutCliError::new(
            "unsupported_thumbnail_type",
            "ツリーで表示できないサムネイル形式です",
            json!({ "media_type": media_type }),
        ));
    }
    if bytes.len() > THUMBNAIL_MAX_BYTES {
        return Err(SproutCliError::new(
            "thumbnail_too_large",
            "サムネイルが表示上限を超えています",
            json!({ "size": bytes.len(), "limit": THUMBNAIL_MAX_BYTES }),
        ));
    }
    Ok(format!("data:{media_type};base64,{}", BASE64.encode(bytes)))
}

#[tauri::command]
fn read_sprout_thumbnail(
    project_dir: String,
    commit_id: String,
    media_type: String,
    sprout_program: Option<String>,
) -> Result<String, SproutCliError> {
    if commit_id.trim().is_empty() {
        return Err(SproutCliError::new(
            "invalid_request",
            "コミットIDが指定されていません",
            json!({}),
        ));
    }
    thumbnail_data_url(&media_type, &[])?;
    let sequence = TEMP_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let output = std::env::temp_dir().join(format!(
        "sprout-gui-thumbnail-{}-{sequence}.bin",
        std::process::id()
    ));
    let args = vec![
        "thumbnail".to_owned(),
        commit_id.clone(),
        "--output".to_owned(),
        output.to_string_lossy().into_owned(),
    ];
    let export_result = run_sprout(project_dir, args, sprout_program);
    if let Err(error) = export_result {
        let _ = fs::remove_file(&output);
        return Err(error);
    }
    let bytes = fs::read(&output).map_err(|error| {
        SproutCliError::new(
            "thumbnail_read_failed",
            "エクスポートしたサムネイルを読み込めませんでした",
            json!({ "commit_id": commit_id, "reason": error.to_string() }),
        )
    });
    let _ = fs::remove_file(&output);
    thumbnail_data_url(&media_type, &bytes?)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .invoke_handler(tauri::generate_handler![run_sprout, read_sprout_thumbnail])
        .run(tauri::generate_context!())
        .expect("error while running Tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn appends_json_once() {
        assert_eq!(
            command_arguments(&["status".to_owned()]),
            vec!["status", "--json"]
        );
        assert_eq!(
            command_arguments(&["status".to_owned(), "--json".to_owned()]),
            vec!["status", "--json"]
        );
    }

    #[test]
    fn preserves_structured_cli_errors_and_adds_exit_code() {
        let error = parse_cli_error(
            r#"{"code":"repository_locked","message":"busy","details":{"retryable":true}}"#,
            Some(1),
        );
        assert_eq!(error.code, "repository_locked");
        assert_eq!(error.message, "busy");
        assert_eq!(error.details["retryable"], true);
        assert_eq!(error.details["exit_code"], 1);
    }

    #[test]
    fn wraps_unstructured_cli_errors() {
        let error = parse_cli_error("unexpected failure", Some(7));
        assert_eq!(error.code, "sprout_cli_failed");
        assert_eq!(error.message, "unexpected failure");
        assert_eq!(error.details["exit_code"], 7);
    }

    #[test]
    fn encodes_supported_thumbnail_data_urls() {
        assert_eq!(
            thumbnail_data_url("image/png", &[1, 2, 3]).unwrap(),
            "data:image/png;base64,AQID"
        );
        let error = thumbnail_data_url("video/mp4", &[1]).unwrap_err();
        assert_eq!(error.code, "unsupported_thumbnail_type");
    }
}
