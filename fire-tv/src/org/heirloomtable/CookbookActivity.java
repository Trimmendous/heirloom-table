package org.heirloomtable;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import java.io.File;
import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class CookbookActivity extends Activity {
    private static final String ASSET_HOST = "cookbook.heirloom.invalid";
    private static final String RELEASE_API = "https://api.github.com/repos/Trimmendous/culinote/releases/latest";
    private static final Pattern APK_URL = Pattern.compile(
        "https://github[.]com/Trimmendous/culinote/releases/download/v?([0-9]{1,3})[.]([0-9]{1,3})[.]([0-9]{1,3})/culinote-fire-tv[.]apk");
    private static final String APK_MIME = "application/vnd.android.package-archive";
    private WebView cookbook;
    private DownloadManager downloads;
    private long downloadId = -1;
    private int updateCode;
    private boolean resumed;
    private boolean ready;
    private final BroadcastReceiver downloadReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (resumed && intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1) == downloadId) {
                completeDownload();
            }
        }
    };

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        downloads = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
        SharedPreferences pending = getPreferences(MODE_PRIVATE);
        downloadId = pending.getLong("downloadId", -1);
        updateCode = pending.getInt("updateCode", 0);
        registerReceiver(downloadReceiver, new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE));
        cookbook = new WebView(this);
        cookbook.setBackgroundColor(0x00000000);
        cookbook.setKeepScreenOn(true);
        WebSettings settings = cookbook.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        cookbook.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if ("GET".equals(request.getMethod()) && RELEASE_API.equals(uri.toString())) return null;
                if ("https".equals(uri.getScheme()) && ASSET_HOST.equals(uri.getHost())) {
                    String path = uri.getPath();
                    if (path != null && path.matches("/[a-zA-Z0-9_./-]+") && !path.contains("..")) {
                        try {
                            String mime = assetMime(path);
                            String charset = mime.startsWith("text/") || mime.equals("application/javascript")
                                ? "UTF-8" : null;
                            return new WebResourceResponse(mime, charset, getAssets().open(path.substring(1)));
                        } catch (IOException missingAsset) {
                            // Return an offline 404 for missing assets.
                        }
                    }
                }
                return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found",
                    Collections.emptyMap(), null);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (request.isForMainFrame()) startUpdateDownload(request.getUrl());
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                ready = true;
            }
        });
        setContentView(cookbook);
        hideSystemBars();
        cookbook.loadUrl("https://" + ASSET_HOST + "/index.html?platform=fire-tv");
    }

    private void startUpdateDownload(Uri uri) {
        Matcher release = APK_URL.matcher(uri.toString());
        if (!release.matches()) return;
        if (downloadId != -1) {
            notifyUpdate("An update download is already in progress.");
            return;
        }
        int code = Integer.parseInt(release.group(1)) * 1000000
            + Integer.parseInt(release.group(2)) * 1000 + Integer.parseInt(release.group(3));
        try {
            if (code <= getPackageManager().getPackageInfo(getPackageName(), 0).versionCode) {
                notifyUpdate("This update is already installed.");
                return;
            }
            File folder = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
            if (folder == null) throw new IllegalStateException("Downloads storage unavailable");
            File target = new File(folder, apkFilename(code));
            if (target.exists() && !target.delete()) throw new IllegalStateException("Cannot replace old download");
            DownloadManager.Request request = new DownloadManager.Request(uri)
                .setTitle("Culinote v" + release.group(1) + "." + release.group(2) + "." + release.group(3))
                .setMimeType(APK_MIME)
                .setDestinationInExternalFilesDir(this, Environment.DIRECTORY_DOWNLOADS, target.getName())
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            downloadId = downloads.enqueue(request);
            updateCode = code;
            getPreferences(MODE_PRIVATE).edit().putLong("downloadId", downloadId)
                .putInt("updateCode", updateCode).apply();
            notifyUpdate("Downloading the update...");
        } catch (PackageManager.NameNotFoundException | RuntimeException unavailable) {
            notifyUpdate("Could not start the update download.");
        }
    }

    private static String apkFilename(int code) {
        return "culinote-fire-tv-" + code + ".apk";
    }

    private void completeDownload() {
        if (downloadId == -1) return;
        long completedId = downloadId;
        try (Cursor cursor = downloads.query(new DownloadManager.Query().setFilterById(completedId))) {
            if (cursor == null || !cursor.moveToFirst()) {
                clearPendingDownload();
                notifyUpdate("The update download is unavailable.");
                return;
            }
            int status = cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS));
            if (status != DownloadManager.STATUS_FAILED && status != DownloadManager.STATUS_SUCCESSFUL) return;
            clearPendingDownload();
            if (status == DownloadManager.STATUS_FAILED) {
                notifyUpdate("Update download failed. Try Update Now again.");
                return;
            }
            File folder = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
            if (folder == null || !isMatchingUpdate(new File(folder, apkFilename(updateCode)))) {
                downloads.remove(completedId);
                notifyUpdate("The downloaded APK does not match this app and version.");
                return;
            }
            Uri apk = downloads.getUriForDownloadedFile(completedId);
            if (apk != null) {
                startActivity(new Intent(Intent.ACTION_VIEW)
                    .setDataAndType(apk, APK_MIME)
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION));
            } else {
                notifyUpdate("APK downloaded. Open it from Downloads to install.");
            }
        } catch (ActivityNotFoundException | SecurityException unavailable) {
            notifyUpdate("APK downloaded. The installer could not open it on this device.");
        }
    }

    private void clearPendingDownload() {
        downloadId = -1;
        getPreferences(MODE_PRIVATE).edit().remove("downloadId").remove("updateCode").apply();
    }

    @SuppressWarnings("deprecation")
    private boolean isMatchingUpdate(File apk) {
        try {
            PackageManager manager = getPackageManager();
            PackageInfo installed = manager.getPackageInfo(getPackageName(), PackageManager.GET_SIGNATURES);
            PackageInfo update = manager.getPackageArchiveInfo(apk.getPath(), PackageManager.GET_SIGNATURES);
            return update != null && getPackageName().equals(update.packageName)
                && update.versionCode == updateCode && update.versionCode > installed.versionCode
                && update.signatures != null && Arrays.equals(installed.signatures, update.signatures);
        } catch (PackageManager.NameNotFoundException unavailable) {
            return false;
        }
    }

    private void notifyUpdate(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    @Override
    protected void onResume() {
        super.onResume();
        resumed = true;
        completeDownload();
    }

    @Override
    protected void onPause() {
        resumed = false;
        super.onPause();
    }

    private static String assetMime(String path) {
        if (path.endsWith(".html")) return "text/html";
        if (path.endsWith(".css")) return "text/css";
        if (path.endsWith(".js")) return "application/javascript";
        if (path.endsWith(".ttf")) return "font/ttf";
        if (path.endsWith(".png")) return "image/png";
        if (path.endsWith(".jpg")) return "image/jpeg";
        return "application/octet-stream";
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemBars();
    }

    @SuppressWarnings("deprecation")
    private void hideSystemBars() {
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        String command = remoteCommand(event.getKeyCode());
        if (command == null) return super.dispatchKeyEvent(event);
        if (event.getAction() == KeyEvent.ACTION_DOWN
                && (event.getRepeatCount() == 0 || isDirection(event.getKeyCode()))) {
            if (ready) {
                cookbook.evaluateJavascript(
                    "pressKey('" + command + "'); Boolean(m.top.exitApp);",
                    result -> {
                        if ("true".equals(result)) finish();
                    });
            } else if ("back".equals(command)) {
                finish();
            }
        }
        return true;
    }

    private static boolean isDirection(int keyCode) {
        return keyCode == KeyEvent.KEYCODE_DPAD_UP || keyCode == KeyEvent.KEYCODE_DPAD_DOWN
            || keyCode == KeyEvent.KEYCODE_DPAD_LEFT || keyCode == KeyEvent.KEYCODE_DPAD_RIGHT;
    }

    private static String remoteCommand(int keyCode) {
        switch (keyCode) {
            case KeyEvent.KEYCODE_DPAD_UP: return "up";
            case KeyEvent.KEYCODE_DPAD_DOWN: return "down";
            case KeyEvent.KEYCODE_DPAD_LEFT: return "left";
            case KeyEvent.KEYCODE_DPAD_RIGHT: return "right";
            case KeyEvent.KEYCODE_DPAD_CENTER:
            case KeyEvent.KEYCODE_ENTER: return "OK";
            case KeyEvent.KEYCODE_BACK: return "back";
            case KeyEvent.KEYCODE_MENU: return "options";
            case KeyEvent.KEYCODE_MEDIA_PLAY:
            case KeyEvent.KEYCODE_MEDIA_PAUSE:
            case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE: return "play";
            case KeyEvent.KEYCODE_MEDIA_REWIND: return "rewind";
            case KeyEvent.KEYCODE_MEDIA_FAST_FORWARD: return "fastforward";
            default: return null;
        }
    }

    @Override
    protected void onDestroy() {
        ready = false;
        unregisterReceiver(downloadReceiver);
        setContentView(new View(this));
        cookbook.destroy();
        super.onDestroy();
    }
}
