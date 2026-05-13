import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";
import fs from "fs";

const packageJsonPath = path.resolve(__dirname, "package.json");
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf-8"));

export default defineConfig(({ mode }) => ({
  define: {
    APP_VERSION: JSON.stringify(process.env.VITE_APP_VERSION || packageJson.version),
  },
  server: {
    host: "localhost",
    port: 8080,
  },
  optimizeDeps: {
    include: [
      'react', 'react-dom', 'react-router-dom',
      '@tanstack/react-query',
      'axios',
      'date-fns',
      'lucide-react',
      'sonner',
      'recharts',
      'framer-motion',
      '@radix-ui/react-dialog',
      '@radix-ui/react-select',
      '@radix-ui/react-tabs',
      '@radix-ui/react-checkbox',
      '@radix-ui/react-alert-dialog',
    ],
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "web-worker": path.resolve(__dirname, "./src/lib/empty-module.ts"),
    },
  },
  envPrefix: "VITE_",
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-query': ['@tanstack/react-query'],
          'vendor-ui': ['@radix-ui/react-dialog', '@radix-ui/react-select', '@radix-ui/react-tabs'],
          'vendor-charts': ['recharts'],
          'vendor-flow': ['@xyflow/react', 'elkjs'],
          'vendor-motion': ['framer-motion'],
          'vendor-xlsx': ['xlsx'],
        },
      },
    },
  },
}));
