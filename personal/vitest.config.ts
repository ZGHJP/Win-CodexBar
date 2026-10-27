import base from "../apps/desktop-tauri/vite.config";

export default {
  ...base,
  test: {
    ...base.test,
    setupFiles: [...base.test.setupFiles, "../../personal/test-locale.mjs"],
  },
};
