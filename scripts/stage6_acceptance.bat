@echo off
setlocal

pushd "%~dp0..\frontend" || exit /b 1

call npm test -- ^
  src/stores/__tests__/usePreferenceStore.spec.js ^
  src/stores/__tests__/workbenchStores.spec.js ^
  src/components/workspace/__tests__/ManualSyncButton.spec.js ^
  src/components/workspace/__tests__/WritingPreferencePanel.spec.js ^
  src/components/workspace/__tests__/PureTextEditor.spec.js ^
  src/components/workspace/__tests__/StatusBar.spec.js ^
  src/components/workspace/__tests__/AssetRail.spec.js ^
  src/components/workspace/__tests__/AssetDrawer.spec.js ^
  src/components/workspace/__tests__/ChapterSidebar.spec.js ^
  src/views/__tests__/WritingStudio.spec.js

set EXIT_CODE=%ERRORLEVEL%
popd

exit /b %EXIT_CODE%
