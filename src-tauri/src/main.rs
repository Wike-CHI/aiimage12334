#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

#[tauri::command]
async fn open_devtools(window: tauri::Window) {
    if let Err(e) = window.open_devtools() {
        eprintln!("Failed to open devtools: {}", e);
    }
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![open_devtools])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
