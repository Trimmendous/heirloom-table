#!/usr/bin/env bash
# Build and sign an offline Fire OS APK using the shared web assets.
set -euo pipefail
cd "$(dirname "$0")/.."

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [[ -z "$SDK" ]]; then
  echo "Set ANDROID_HOME to the Android SDK with platforms;android-35 and build-tools;35.0.0 installed." >&2
  exit 1
fi
TOOLS="$SDK/build-tools/35.0.0"
PLATFORM="$SDK/platforms/android-35/android.jar"
JAVAC="${JAVA_HOME:+$JAVA_HOME/bin/}javac"
KEYTOOL="${JAVA_HOME:+$JAVA_HOME/bin/}keytool"
ZIP="$(command -v zip)"
if [[ ! -f "$PLATFORM" || ! -x "$TOOLS/aapt2" || ! -x "$TOOLS/d8" || ! -x "$TOOLS/zipalign" || ! -x "$TOOLS/apksigner" ]]; then
  echo "Install Android SDK packages platforms;android-35 and build-tools;35.0.0." >&2
  exit 1
fi

python3 tools/build_data.py
python3 tools/check_assets.py
read -r VERSION CODE < <(python3 -c 'import json; app = json.load(open("roku/data/recipes.json"))["app"]; print(app["version"], app["versionCode"])')
mkdir -p dist
WORK="$(mktemp -d "$PWD/dist/fire-tv-build.XXXXXX")"
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/classes" "$WORK/dex" "$WORK/res/drawable-nodpi"
cp -R fire-tv/res/. "$WORK/res/"
cp roku/images/channel/fire_tv_banner.png "$WORK/res/drawable-nodpi/tile.png"
cp roku/images/channel/culinote_mark.png "$WORK/res/drawable-nodpi/mark.png"
cp roku/images/channel/splash_fhd.jpg "$WORK/res/drawable-nodpi/splash.jpg"
"$TOOLS/aapt2" compile --dir "$WORK/res" -o "$WORK/resources.zip"
"$TOOLS/aapt2" link -I "$PLATFORM" --manifest fire-tv/AndroidManifest.xml \
  --version-name "$VERSION" --version-code "$CODE" \
  -A web "$WORK/resources.zip" -o "$WORK/unsigned.apk"

"$JAVAC" --release 8 -classpath "$PLATFORM" -d "$WORK/classes" fire-tv/src/org/heirloomtable/CookbookActivity.java
"$TOOLS/d8" --min-api 25 --lib "$PLATFORM" --output "$WORK/dex" "$WORK"/classes/org/heirloomtable/*.class
(cd "$WORK/dex" && "$ZIP" -q -X "$WORK/unsigned.apk" classes.dex)
"$TOOLS/zipalign" -f 4 "$WORK/unsigned.apk" "$WORK/aligned.apk"

# Keep the same local signing key so future sideload builds can upgrade in place.
KEYSTORE=dist/heirloom-fire-tv-debug.p12
if [[ ! -f "$KEYSTORE" ]]; then
  "$KEYTOOL" -genkeypair -keystore "$KEYSTORE" -storetype PKCS12 \
    -alias heirloom-debug -storepass android -keypass android \
    -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Heirloom Table Debug"
fi
"$TOOLS/apksigner" sign --ks "$KEYSTORE" --ks-key-alias heirloom-debug \
  --ks-pass pass:android --key-pass pass:android --out "$WORK/culinote-fire-tv.apk" "$WORK/aligned.apk"
"$TOOLS/apksigner" verify --verbose "$WORK/culinote-fire-tv.apk"
"$TOOLS/zipalign" -c 4 "$WORK/culinote-fire-tv.apk"
mv "$WORK/culinote-fire-tv.apk" dist/culinote-fire-tv.apk
echo "Built dist/culinote-fire-tv.apk"
