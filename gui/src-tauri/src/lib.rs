use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};
use serde::Serialize;
use serde_json::{Value, json};
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::Mutex;
use std::sync::atomic::{AtomicU64, Ordering};

const CREATE_NO_WINDOW: u32 = 0x0800_0000;
const THUMBNAIL_MAX_BYTES: usize = 2 * 1024 * 1024;
static TEMP_SEQUENCE: AtomicU64 = AtomicU64::new(0);
const PASTE_DIR_PREFIX: &str = "sprout-gui-paste-";

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

/// One long-lived `sprout serve` process reused across GUI requests.
struct ServeClient {
    program: String,
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
    next_id: u64,
}

impl ServeClient {
    fn spawn(program: &str) -> Result<Option<Self>, SproutCliError> {
        let mut command = Command::new(program);
        command
            .arg("serve")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        configure(&mut command);
        let mut child = command.spawn().map_err(|error| spawn_error(program, &error))?;
        let (Some(stdin), Some(stdout)) = (child.stdin.take(), child.stdout.take()) else {
            let _ = child.kill();
            return Ok(None);
        };
        let mut stdout = BufReader::new(stdout);
        let mut ready = String::new();
        let started = stdout.read_line(&mut ready).ok().filter(|read| *read > 0).is_some()
            && serde_json::from_str::<Value>(&ready)
                .ok()
                .and_then(|value| value.get("ready").and_then(Value::as_bool))
                == Some(true);
        if !started {
            // Older CLIs without serve exit immediately; fall back to one process per call.
            let _ = child.kill();
            let _ = child.wait();
            return Ok(None);
        }
        Ok(Some(Self {
            program: program.to_owned(),
            child,
            stdin,
            stdout,
            next_id: 0,
        }))
    }

    fn request(&mut self, project: &Path, args: &[String]) -> std::io::Result<Value> {
        self.next_id += 1;
        let request = json!({
            "id": self.next_id,
            "args": args,
            "cwd": project.to_string_lossy(),
        });
        writeln!(self.stdin, "{request}")?;
        self.stdin.flush()?;
        let mut line = String::new();
        if self.stdout.read_line(&mut line)? == 0 {
            return Err(std::io::Error::new(
                std::io::ErrorKind::UnexpectedEof,
                "sprout serve stopped",
            ));
        }
        serde_json::from_str(&line)
            .map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error))
    }
}

impl Drop for ServeClient {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

#[derive(Default)]
struct ServeState {
    client: Mutex<Option<ServeClient>>,
    unsupported: Mutex<Option<String>>,
}

fn configure(command: &mut Command) {
    command
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8")
        .env("NO_COLOR", "1");

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(CREATE_NO_WINDOW);
    }
}

fn spawn_error(program: &str, error: &std::io::Error) -> SproutCliError {
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
}

fn serve_response(response: Value) -> Result<Value, SproutCliError> {
    if response.get("ok").and_then(Value::as_bool) == Some(true) {
        return Ok(response.get("result").cloned().unwrap_or(Value::Null));
    }
    let exit_code = response.get("exit_code").cloned().unwrap_or(Value::Null);
    let error = response.get("error").cloned().unwrap_or_else(|| json!({}));
    let mut details = error.get("details").cloned().unwrap_or_else(|| json!({}));
    if let Some(object) = details.as_object_mut() {
        object.insert("exit_code".to_owned(), exit_code);
    }
    Err(SproutCliError::new(
        error.get("code").and_then(Value::as_str).unwrap_or("sprout_cli_failed"),
        error
            .get("message")
            .and_then(Value::as_str)
            .unwrap_or("Sprout CLIがエラー終了しました"),
        details,
    ))
}

/// Run through the resident serve process, or `None` when it cannot be used.
fn run_via_serve(
    state: &ServeState,
    program: &str,
    project: &Path,
    args: &[String],
) -> Result<Option<Value>, SproutCliError> {
    if state.unsupported.lock().unwrap().as_deref() == Some(program) {
        return Ok(None);
    }
    let mut guard = state.client.lock().unwrap();
    if guard.as_ref().is_some_and(|client| client.program != program) {
        *guard = None;
    }
    if guard.is_none() {
        match ServeClient::spawn(program)? {
            Some(client) => *guard = Some(client),
            None => {
                *state.unsupported.lock().unwrap() = Some(program.to_owned());
                return Ok(None);
            }
        }
    }
    let client = guard.as_mut().expect("serve client was just started");
    match client.request(project, args) {
        Ok(response) => serve_response(response).map(Some),
        Err(_) => {
            // A broken pipe drops the process; this call runs once without it.
            *guard = None;
            Ok(None)
        }
    }
}

fn execute(
    state: &ServeState,
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
    if let Some(value) = run_via_serve(state, program, project, &arguments)? {
        return Ok(value);
    }
    let mut command = Command::new(program);
    command.current_dir(project).args(arguments);
    configure(&mut command);

    let output = command
        .output()
        .map_err(|error| spawn_error(program, &error))?;

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

#[tauri::command]
fn run_sprout(
    state: tauri::State<'_, ServeState>,
    project_dir: String,
    args: Vec<String>,
    sprout_program: Option<String>,
) -> Result<Value, SproutCliError> {
    execute(&state, project_dir, args, sprout_program)
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
    state: tauri::State<'_, ServeState>,
    project_dir: String,
    commit_id: String,
    media_type: String,
    sprout_program: Option<String>,
) -> Result<String, SproutCliError> {
    if commit_id.trim().is_empty() {
        return Err(SproutCliError::new(
            "invalid_request",
            "葉のIDが指定されていません",
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
    let export_result = execute(&state, project_dir, args, sprout_program);
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

fn pasted_thumbnail_extension(media_type: &str) -> Result<&'static str, SproutCliError> {
    match media_type {
        "image/png" => Ok("png"),
        "image/jpeg" => Ok("jpg"),
        "image/webp" => Ok("webp"),
        _ => Err(SproutCliError::new(
            "unsupported_thumbnail_type",
            "貼り付けた画像はサムネイルに使えない形式です（PNG・JPEG・WebPに対応）",
            json!({ "media_type": media_type }),
        )),
    }
}

/// Write pasted image bytes to a fresh directory so the CLI records a plain file name.
fn write_pasted_thumbnail(root: &Path, media_type: &str, data: &str) -> Result<PathBuf, SproutCliError> {
    let extension = pasted_thumbnail_extension(media_type)?;
    let bytes = BASE64.decode(data).map_err(|error| {
        SproutCliError::new(
            "invalid_clipboard_image",
            "貼り付けた画像を読み込めませんでした",
            json!({ "reason": error.to_string() }),
        )
    })?;
    if bytes.is_empty() {
        return Err(SproutCliError::new("invalid_clipboard_image", "貼り付けた画像が空です", json!({})));
    }
    if bytes.len() > THUMBNAIL_MAX_BYTES {
        return Err(SproutCliError::new(
            "thumbnail_too_large",
            "貼り付けた画像がサムネイルの上限（2 MiB）を超えています",
            json!({ "size": bytes.len(), "limit": THUMBNAIL_MAX_BYTES }),
        ));
    }
    let sequence = TEMP_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let directory = root.join(format!("{PASTE_DIR_PREFIX}{}-{sequence}", std::process::id()));
    let path = directory.join(format!("clipboard.{extension}"));
    let written = fs::create_dir(&directory).and_then(|()| fs::write(&path, &bytes));
    if let Err(error) = written {
        let _ = fs::remove_dir_all(&directory);
        return Err(SproutCliError::new(
            "clipboard_image_write_failed",
            "貼り付けた画像を一時ファイルへ保存できませんでした",
            json!({ "reason": error.to_string() }),
        ));
    }
    Ok(path)
}

/// Remove a file created by write_pasted_thumbnail; other paths are refused.
fn remove_pasted_thumbnail(root: &Path, path: &Path) -> Result<(), SproutCliError> {
    let directory = path.parent().filter(|directory| {
        directory.parent() == Some(root)
            && directory
                .file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.starts_with(PASTE_DIR_PREFIX))
    });
    let Some(directory) = directory else {
        return Err(SproutCliError::new(
            "invalid_request",
            "貼り付け用の一時ファイルではありません",
            json!({ "path": path.to_string_lossy() }),
        ));
    };
    let _ = fs::remove_file(path);
    let _ = fs::remove_dir(directory);
    Ok(())
}

#[tauri::command]
fn save_pasted_thumbnail(media_type: String, data: String) -> Result<String, SproutCliError> {
    write_pasted_thumbnail(&std::env::temp_dir(), &media_type, &data)
        .map(|path| path.to_string_lossy().into_owned())
}

#[tauri::command]
fn discard_pasted_thumbnail(path: String) -> Result<(), SproutCliError> {
    remove_pasted_thumbnail(&std::env::temp_dir(), Path::new(&path))
}

/// Keep clipboard names inside a dedicated temporary directory, preserving extensions.
fn write_pasted_preview(root: &Path, name: &str, data: &str) -> Result<PathBuf, SproutCliError> {
    if name.is_empty() || name == "." || name == ".."
        || name.chars().any(|c| c.is_control() || "<>:\"/\\|?*".contains(c))
        || name.ends_with('.') || name.ends_with(' ')
    {
        return Err(SproutCliError::new("invalid_clipboard_name", "貼り付けたファイル名を使用できません", json!({ "name": name })));
    }
    let stem = name.split('.').next().unwrap_or("").to_ascii_uppercase();
    let reserved = matches!(stem.as_str(), "CON" | "PRN" | "AUX" | "NUL")
        || (stem.len() == 4 && (stem.starts_with("COM") || stem.starts_with("LPT"))
            && matches!(stem.as_bytes()[3], b'1'..=b'9'));
    if reserved {
        return Err(SproutCliError::new("invalid_clipboard_name", "予約されたファイル名です", json!({ "name": name })));
    }
    let bytes = BASE64.decode(data).map_err(|error| SproutCliError::new(
        "invalid_clipboard_file", "貼り付けたファイルを読み込めませんでした", json!({ "reason": error.to_string() })
    ))?;
    let sequence = TEMP_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let directory = root.join(format!("{PASTE_DIR_PREFIX}{}-{sequence}", std::process::id()));
    let path = directory.join(name);
    fs::create_dir(&directory).map_err(|error| SproutCliError::new(
        "clipboard_file_write_failed", "一時フォルダを作成できませんでした", json!({ "reason": error.to_string() })
    ))?;
    if let Err(error) = fs::write(&path, bytes) {
        let _ = fs::remove_file(&path);
        let _ = fs::remove_dir(&directory);
        return Err(SproutCliError::new("clipboard_file_write_failed", "一時ファイルを保存できませんでした", json!({ "reason": error.to_string() })));
    }
    Ok(path)
}

#[tauri::command]
fn save_pasted_preview(name: String, data: String) -> Result<String, SproutCliError> {
    write_pasted_preview(&std::env::temp_dir(), &name, &data)
        .map(|path| path.to_string_lossy().into_owned())
}

/// Explorer exposes copied files as CF_HDROP, which WebView clipboard files may omit.
#[tauri::command]
fn read_clipboard_files() -> Result<Vec<String>, SproutCliError> {
    #[cfg(windows)]
    {
        use std::ffi::c_void;
        #[link(name = "user32")]
        unsafe extern "system" {
            fn OpenClipboard(owner: *mut c_void) -> i32;
            fn CloseClipboard() -> i32;
            fn GetClipboardData(format: u32) -> *mut c_void;
            fn IsClipboardFormatAvailable(format: u32) -> i32;
        }
        #[link(name = "shell32")]
        unsafe extern "system" {
            fn DragQueryFileW(drop: *mut c_void, index: u32, file: *mut u16, size: u32) -> u32;
        }
        // All clipboard handles are borrowed and remain valid until CloseClipboard.
        unsafe {
            if IsClipboardFormatAvailable(15) == 0 { return Ok(vec![]); }
            if OpenClipboard(std::ptr::null_mut()) == 0 {
                return Err(SproutCliError::new("clipboard_busy", "クリップボードを開けません。再度貼り付けてください", json!({})));
            }
            struct ClipboardGuard;
            impl Drop for ClipboardGuard {
                fn drop(&mut self) { unsafe { CloseClipboard(); } }
            }
            let _guard = ClipboardGuard;
            let drop = GetClipboardData(15);
            if drop.is_null() { return Ok(vec![]); }
            let count = DragQueryFileW(drop, u32::MAX, std::ptr::null_mut(), 0);
            let mut paths = Vec::new();
            for index in 0..count {
                let length = DragQueryFileW(drop, index, std::ptr::null_mut(), 0);
                let mut buffer = vec![0u16; length as usize + 1];
                let copied = DragQueryFileW(drop, index, buffer.as_mut_ptr(), buffer.len() as u32);
                paths.push(String::from_utf16_lossy(&buffer[..copied as usize]));
            }
            return Ok(paths);
        }
    }
    #[cfg(not(windows))]
    Ok(vec![])
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .manage(ServeState::default())
        .invoke_handler(tauri::generate_handler![
            run_sprout,
            read_sprout_thumbnail,
            save_pasted_thumbnail,
            save_pasted_preview,
            read_clipboard_files,
            discard_pasted_thumbnail
        ])
        .run(tauri::generate_context!())
        .expect("error while running Tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn preview_paste_preserves_arbitrary_files_and_cleans_up() {
        let root = std::env::temp_dir();
        let path = write_pasted_preview(&root, "voice.wav", &BASE64.encode(b"arbitrary bytes")).unwrap();
        assert_eq!(path.file_name().unwrap(), "voice.wav");
        assert_eq!(fs::read(&path).unwrap(), b"arbitrary bytes");
        remove_pasted_thumbnail(&root, &path).unwrap();
        assert!(!path.exists());
        let empty = write_pasted_preview(&root, "empty.bin", "").unwrap();
        assert_eq!(fs::metadata(&empty).unwrap().len(), 0);
        remove_pasted_thumbnail(&root, &empty).unwrap();
    }

    #[test]
    fn preview_paste_rejects_unsafe_names_and_invalid_base64() {
        for name in ["../escape.bin", "a\\b", "C:escape", "..", "", "CON.txt", "bad."] {
            assert!(write_pasted_preview(&std::env::temp_dir(), name, "AA==").is_err());
        }
        assert!(write_pasted_preview(&std::env::temp_dir(), "file.bin", "invalid base64!").is_err());
    }

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
    fn maps_serve_responses() {
        let ok = serve_response(json!({"id": 1, "ok": true, "exit_code": 0, "result": {"a": 1}}));
        assert_eq!(ok.unwrap()["a"], 1);
        let error = serve_response(json!({
            "id": 2,
            "ok": false,
            "exit_code": 1,
            "error": {"code": "repository_locked", "message": "busy", "details": {"retryable": true}}
        }))
        .unwrap_err();
        assert_eq!(error.code, "repository_locked");
        assert_eq!(error.message, "busy");
        assert_eq!(error.details["retryable"], true);
        assert_eq!(error.details["exit_code"], 1);
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

    #[test]
    fn writes_and_discards_pasted_thumbnails() {
        let root = std::env::temp_dir().join(format!("sprout-gui-paste-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir(&root).unwrap();

        let path = write_pasted_thumbnail(&root, "image/png", "AQID").unwrap();
        assert_eq!(path.file_name().unwrap(), "clipboard.png");
        assert_eq!(fs::read(&path).unwrap(), vec![1, 2, 3]);
        remove_pasted_thumbnail(&root, &path).unwrap();
        assert!(!path.exists());
        assert!(!path.parent().unwrap().exists());

        let other = root.join("keep.png");
        fs::write(&other, [1]).unwrap();
        assert_eq!(remove_pasted_thumbnail(&root, &other).unwrap_err().code, "invalid_request");
        assert!(other.exists());

        assert_eq!(write_pasted_thumbnail(&root, "image/gif", "AQID").unwrap_err().code, "unsupported_thumbnail_type");
        assert_eq!(write_pasted_thumbnail(&root, "image/png", "!!").unwrap_err().code, "invalid_clipboard_image");
        let large = BASE64.encode(vec![0; THUMBNAIL_MAX_BYTES + 1]);
        assert_eq!(write_pasted_thumbnail(&root, "image/png", &large).unwrap_err().code, "thumbnail_too_large");
        fs::remove_dir_all(&root).unwrap();
    }
}
