//! WinSparkle auto-updates — the Windows counterpart of Sparkle on macOS.
//!
//! `WinSparkle.dll` ships next to the exe (see `tauri.windows.conf.json`) and is
//! loaded at runtime by full path, so a missing or broken DLL costs only the
//! updater: every failure here logs a warning and the app starts regardless.
//!
//! It reads the same kind of appcast as Sparkle and verifies the same EdDSA
//! signature, so the Mac build's key and Sparkle's `sign_update` sign the
//! installer (the skill's `make_windows_appcast.sh`).
//!
//! Wire-up in lib.rs: `#[cfg(target_os = "windows")] mod winsparkle;`, call
//! `winsparkle::init(app.handle())` in `.setup`, and `winsparkle::cleanup()` on
//! `RunEvent::Exit`. Cargo.toml: `libloading = "0.8"` under
//! `[target.'cfg(target_os = "windows")'.dependencies]`.

use std::ffi::{c_char, c_int, CString, OsStr};
use std::os::windows::ffi::OsStrExt;
use std::path::PathBuf;
use std::sync::OnceLock;

use libloading::Library;
use tauri::{AppHandle, Manager};

// The Windows feed — its own file, never the macOS appcast.
const APPCAST_URL: &str = "__APPCAST_URL__";
// Public half of the Sparkle EdDSA key — the same SUPublicEDKey as the Mac build.
const EDDSA_PUBLIC_KEY: &str = "__EDDSA_PUBLIC_KEY__";

// Signatures from include/winsparkle.h (WinSparkle 0.9.4). All are __cdecl,
// which on x64/ARM64 is the one C calling convention.
struct Api {
  init: unsafe extern "C" fn(),
  cleanup: unsafe extern "C" fn(),
  set_appcast_url: unsafe extern "C" fn(*const c_char),
  set_eddsa_public_key: unsafe extern "C" fn(*const c_char) -> c_int,
  set_app_details: unsafe extern "C" fn(*const u16, *const u16, *const u16),
  set_app_build_version: unsafe extern "C" fn(*const u16),
  set_automatic_check_for_updates: unsafe extern "C" fn(c_int),
  set_can_shutdown_callback: unsafe extern "C" fn(extern "C" fn() -> c_int),
  set_shutdown_request_callback: unsafe extern "C" fn(extern "C" fn()),
  check_update_with_ui: unsafe extern "C" fn(),
}

// The Library stays loaded for the life of the process: WinSparkle's own
// threads run its code until `cleanup`. API is set only once init has run.
static LIB: OnceLock<Library> = OnceLock::new();
static API: OnceLock<Api> = OnceLock::new();
static APP: OnceLock<AppHandle> = OnceLock::new();

fn wide(s: &str) -> Vec<u16> {
  OsStr::new(s).encode_wide().chain(std::iter::once(0)).collect()
}

fn dll_candidates(app: &AppHandle) -> Vec<PathBuf> {
  let mut dirs = Vec::new();
  // On Windows the resource dir is the exe's own folder.
  if let Ok(dir) = app.path().resource_dir() {
    dirs.push(dir);
  }
  if let Some(dir) = std::env::current_exe().ok().and_then(|p| p.parent().map(PathBuf::from)) {
    dirs.push(dir);
  }
  dirs.into_iter().map(|d| d.join("WinSparkle.dll")).collect()
}

fn sym<T: Copy>(lib: &'static Library, name: &str) -> Result<T, String> {
  let cname = format!("{name}\0");
  // SAFETY: the function types in Api match winsparkle.h.
  unsafe { lib.get::<T>(cname.as_bytes()) }
    .map(|s| *s)
    .map_err(|e| format!("{name}: {e}"))
}

fn load(app: &AppHandle) -> Result<Api, String> {
  let path = dll_candidates(app)
    .into_iter()
    .find(|p| p.is_file())
    .ok_or("WinSparkle.dll not found next to the app")?;
  // SAFETY: WinSparkle's DllMain does no work beyond its own initialisation.
  let lib = unsafe { Library::new(&path) }
    .map_err(|e| format!("cannot load {}: {e}", path.display()))?;
  let lib = LIB.get_or_init(|| lib);

  Ok(Api {
    init: sym(lib, "win_sparkle_init")?,
    cleanup: sym(lib, "win_sparkle_cleanup")?,
    set_appcast_url: sym(lib, "win_sparkle_set_appcast_url")?,
    set_eddsa_public_key: sym(lib, "win_sparkle_set_eddsa_public_key")?,
    set_app_details: sym(lib, "win_sparkle_set_app_details")?,
    set_app_build_version: sym(lib, "win_sparkle_set_app_build_version")?,
    set_automatic_check_for_updates: sym(lib, "win_sparkle_set_automatic_check_for_updates")?,
    set_can_shutdown_callback: sym(lib, "win_sparkle_set_can_shutdown_callback")?,
    set_shutdown_request_callback: sym(lib, "win_sparkle_set_shutdown_request_callback")?,
    check_update_with_ui: sym(lib, "win_sparkle_check_update_with_ui")?,
  })
}

// Both callbacks run on a WinSparkle thread, never the main one.
extern "C" fn can_shutdown() -> c_int {
  1
}

// Called right after the installer has been launched: get out of its way.
extern "C" fn shutdown_request() {
  if let Some(app) = APP.get() {
    app.exit(0);
  }
}

/// Configures and starts WinSparkle. Never fails the app — problems are logged.
pub fn init(app: &AppHandle) {
  if let Err(e) = try_init(app) {
    log::warn!("WinSparkle disabled: {e}");
  }
}

fn try_init(app: &AppHandle) -> Result<(), String> {
  let api = load(app)?;
  let _ = APP.set(app.clone());

  let config = app.config();
  let company = config.bundle.publisher.clone().unwrap_or_else(|| "__COMPANY__".into());
  let product = config.product_name.clone().unwrap_or_else(|| "__PRODUCT__".into());
  let version = app.package_info().version.to_string();

  let url = CString::new(APPCAST_URL).expect("no NUL in URL");
  let key = CString::new(EDDSA_PUBLIC_KEY).expect("no NUL in key");
  let (company, product, version) = (wide(&company), wide(&product), wide(&version));

  // SAFETY: every set_* call precedes init, as WinSparkle requires; the strings
  // are NUL-terminated and WinSparkle copies them.
  unsafe {
    (api.set_appcast_url)(url.as_ptr());
    if (api.set_eddsa_public_key)(key.as_ptr()) != 1 {
      return Err("EdDSA public key rejected".into());
    }
    // company + product name the registry key (HKCU\Software\<company>\<app>\WinSparkle).
    // The same version goes to both: the build version is what is compared with
    // the appcast's sparkle:version, the display one with sparkle:shortVersionString.
    (api.set_app_details)(company.as_ptr(), product.as_ptr(), version.as_ptr());
    (api.set_app_build_version)(version.as_ptr());
    (api.set_automatic_check_for_updates)(1);
    (api.set_can_shutdown_callback)(can_shutdown);
    (api.set_shutdown_request_callback)(shutdown_request);
    (api.init)();
  }
  let _ = API.set(api);
  Ok(())
}

/// The manual check behind ⟳. WinSparkle draws its own UI.
pub fn check_with_ui() -> Result<(), String> {
  let api = API.get().ok_or("the updater is not available")?;
  // SAFETY: API is set only after a successful init.
  unsafe { (api.check_update_with_ui)() };
  Ok(())
}

pub fn cleanup() {
  if let Some(api) = API.get() {
    // SAFETY: WinSparkle tolerates cleanup at exit, after init.
    unsafe { (api.cleanup)() };
  }
}
