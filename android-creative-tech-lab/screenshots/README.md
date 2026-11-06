# Screenshots

**No synthetic images are presented as screenshots.**

The GitHub Actions workflow builds and launches the Android app on an emulator, navigates through its four tabs and captures:

- 01-overview.png: Coil image + Lottie animation
- 02-sceneview.png: procedural 3D SceneView
- 03-audio.png: waveform and interactive slider
- 04-charts.png: Vico interactive chart

If PNGs are missing, the workflow has not yet completed successfully. Run the app in Android Studio and save authentic screenshots here, then commit them.

For manual captures using adb, while the app is running:
```sh
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png screenshots/01-overview.png
```
