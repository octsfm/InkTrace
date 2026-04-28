// vite.config.js
import { defineConfig } from "file:///D:/Work/InkTrace/ink-trace/frontend/node_modules/vite/dist/node/index.js";
import vue from "file:///D:/Work/InkTrace/ink-trace/frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import path from "path";
var __vite_injected_original_dirname = "D:\\Work\\InkTrace\\ink-trace\\frontend";
var vite_config_default = defineConfig({
  plugins: [vue()],
  base: "./",
  resolve: {
    alias: {
      "@": path.resolve(__vite_injected_original_dirname, "src")
    }
  },
  server: {
    port: 3e3,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:9527",
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: "dist",
    assetsDir: "assets",
    emptyOutDir: true,
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return;
          if (id.includes("element-plus")) return "ui-element-plus";
          if (id.includes("@element-plus/icons-vue")) return "ui-element-icons";
          if (id.includes("vue-router")) return "vendor-vue-router";
          if (id.includes("pinia")) return "vendor-pinia";
          if (id.includes("axios")) return "vendor-axios";
          if (id.includes("/vue/")) return "vendor-vue-core";
        }
      }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFxXb3JrXFxcXElua1RyYWNlXFxcXGluay10cmFjZVxcXFxmcm9udGVuZFwiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiRDpcXFxcV29ya1xcXFxJbmtUcmFjZVxcXFxpbmstdHJhY2VcXFxcZnJvbnRlbmRcXFxcdml0ZS5jb25maWcuanNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL0Q6L1dvcmsvSW5rVHJhY2UvaW5rLXRyYWNlL2Zyb250ZW5kL3ZpdGUuY29uZmlnLmpzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSdcbmltcG9ydCB2dWUgZnJvbSAnQHZpdGVqcy9wbHVnaW4tdnVlJ1xuaW1wb3J0IHBhdGggZnJvbSAncGF0aCdcblxuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKHtcbiAgcGx1Z2luczogW3Z1ZSgpXSxcbiAgYmFzZTogJy4vJyxcbiAgcmVzb2x2ZToge1xuICAgIGFsaWFzOiB7XG4gICAgICAnQCc6IHBhdGgucmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMnKVxuICAgIH1cbiAgfSxcbiAgc2VydmVyOiB7XG4gICAgcG9ydDogMzAwMCxcbiAgICBwcm94eToge1xuICAgICAgJy9hcGknOiB7XG4gICAgICAgIHRhcmdldDogJ2h0dHA6Ly8xMjcuMC4wLjE6OTUyNycsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZVxuICAgICAgfVxuICAgIH1cbiAgfSxcbiAgYnVpbGQ6IHtcbiAgICBvdXREaXI6ICdkaXN0JyxcbiAgICBhc3NldHNEaXI6ICdhc3NldHMnLFxuICAgIGVtcHR5T3V0RGlyOiB0cnVlLFxuICAgIGNodW5rU2l6ZVdhcm5pbmdMaW1pdDogMTIwMCxcbiAgICByb2xsdXBPcHRpb25zOiB7XG4gICAgICBvdXRwdXQ6IHtcbiAgICAgICAgbWFudWFsQ2h1bmtzKGlkKSB7XG4gICAgICAgICAgaWYgKCFpZC5pbmNsdWRlcygnbm9kZV9tb2R1bGVzJykpIHJldHVyblxuICAgICAgICAgIGlmIChpZC5pbmNsdWRlcygnZWxlbWVudC1wbHVzJykpIHJldHVybiAndWktZWxlbWVudC1wbHVzJ1xuICAgICAgICAgIGlmIChpZC5pbmNsdWRlcygnQGVsZW1lbnQtcGx1cy9pY29ucy12dWUnKSkgcmV0dXJuICd1aS1lbGVtZW50LWljb25zJ1xuICAgICAgICAgIGlmIChpZC5pbmNsdWRlcygndnVlLXJvdXRlcicpKSByZXR1cm4gJ3ZlbmRvci12dWUtcm91dGVyJ1xuICAgICAgICAgIGlmIChpZC5pbmNsdWRlcygncGluaWEnKSkgcmV0dXJuICd2ZW5kb3ItcGluaWEnXG4gICAgICAgICAgaWYgKGlkLmluY2x1ZGVzKCdheGlvcycpKSByZXR1cm4gJ3ZlbmRvci1heGlvcydcbiAgICAgICAgICBpZiAoaWQuaW5jbHVkZXMoJy92dWUvJykpIHJldHVybiAndmVuZG9yLXZ1ZS1jb3JlJ1xuICAgICAgICB9XG4gICAgICB9XG4gICAgfVxuICB9XG59KVxuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUFxUyxTQUFTLG9CQUFvQjtBQUNsVSxPQUFPLFNBQVM7QUFDaEIsT0FBTyxVQUFVO0FBRmpCLElBQU0sbUNBQW1DO0FBSXpDLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVMsQ0FBQyxJQUFJLENBQUM7QUFBQSxFQUNmLE1BQU07QUFBQSxFQUNOLFNBQVM7QUFBQSxJQUNQLE9BQU87QUFBQSxNQUNMLEtBQUssS0FBSyxRQUFRLGtDQUFXLEtBQUs7QUFBQSxJQUNwQztBQUFBLEVBQ0Y7QUFBQSxFQUNBLFFBQVE7QUFBQSxJQUNOLE1BQU07QUFBQSxJQUNOLE9BQU87QUFBQSxNQUNMLFFBQVE7QUFBQSxRQUNOLFFBQVE7QUFBQSxRQUNSLGNBQWM7QUFBQSxNQUNoQjtBQUFBLElBQ0Y7QUFBQSxFQUNGO0FBQUEsRUFDQSxPQUFPO0FBQUEsSUFDTCxRQUFRO0FBQUEsSUFDUixXQUFXO0FBQUEsSUFDWCxhQUFhO0FBQUEsSUFDYix1QkFBdUI7QUFBQSxJQUN2QixlQUFlO0FBQUEsTUFDYixRQUFRO0FBQUEsUUFDTixhQUFhLElBQUk7QUFDZixjQUFJLENBQUMsR0FBRyxTQUFTLGNBQWMsRUFBRztBQUNsQyxjQUFJLEdBQUcsU0FBUyxjQUFjLEVBQUcsUUFBTztBQUN4QyxjQUFJLEdBQUcsU0FBUyx5QkFBeUIsRUFBRyxRQUFPO0FBQ25ELGNBQUksR0FBRyxTQUFTLFlBQVksRUFBRyxRQUFPO0FBQ3RDLGNBQUksR0FBRyxTQUFTLE9BQU8sRUFBRyxRQUFPO0FBQ2pDLGNBQUksR0FBRyxTQUFTLE9BQU8sRUFBRyxRQUFPO0FBQ2pDLGNBQUksR0FBRyxTQUFTLE9BQU8sRUFBRyxRQUFPO0FBQUEsUUFDbkM7QUFBQSxNQUNGO0FBQUEsSUFDRjtBQUFBLEVBQ0Y7QUFDRixDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=
