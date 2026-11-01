// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Notice, { type NoticeData } from "./Notice";
const success: NoticeData = { kind: "success", code: "saved", message: "保存しました", details: {} };
afterEach(() => { cleanup(); vi.useRealTimers(); });
it("dismisses only successes after five seconds and cancels stale timers", () => {
  vi.useFakeTimers();
  const close = vi.fn();
  const { rerender } = render(<Notice notice={success} onClose={close} />);
  act(() => vi.advanceTimersByTime(4999));
  expect(close).not.toHaveBeenCalled();
  act(() => vi.advanceTimersByTime(1));
  expect(close).toHaveBeenCalledOnce();
  close.mockClear();
  rerender(<Notice notice={{ ...success }} onClose={close} />);
  act(() => vi.advanceTimersByTime(1000));
  rerender(<Notice notice={{ ...success, kind: "warning" }} onClose={close} />);
  act(() => vi.advanceTimersByTime(10000));
  expect(close).not.toHaveBeenCalled();
});
it("keeps errors visible and exposes the original message and code", () => {
  vi.useFakeTimers();
  const close = vi.fn();
  render(<Notice notice={{ kind: "error", code: "future_code", message: "original failure", details: { path: "a.txt" } }} onClose={close} />);
  act(() => vi.advanceTimersByTime(30000));
  expect(screen.getByRole("alert").textContent).toContain("original failure");
  expect(screen.getByText("code: future_code")).toBeTruthy();
  expect(close).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "通知を閉じる" }));
  expect(close).toHaveBeenCalledOnce();
});
