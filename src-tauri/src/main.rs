#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

#[tauri::command]
async fn open_devtools(window: tauri::Window) {
    // 使用 Manager trait 获取 WebviewWindow
    if let Some(webview) = window.get_webview_window("main") {
        let _ = webview.open_devtools();
    }
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![open_devtools])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
