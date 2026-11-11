import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "app.aaroh.lifeos",
  appName: "AAROH",
  webDir: "dist",
  android: { allowMixedContent: false },
  plugins: {
    LocalNotifications: { iconColor: "#5B5BD6" },
  },
};

export default config;
