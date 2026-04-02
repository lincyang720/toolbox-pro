/**
 * 兑换码管理文件
 *
 * 使用方法：
 *   1. 用户付款后，你发给他一个兑换码
 *   2. 在下方对应产品的数组里添加新兑换码
 *   3. 推送到 GitHub 即可生效（Vercel 自动部署）
 *
 * 格式：
 *   "兑换码": { used: false, download: "下载链接" }
 */
window.CODES = {
  // 磁盘清理工具兑换码
  "disk-cleaner": {
    "DISK-DEMO-2024": {
      used: false,
      download: "https://github.com/YOUR_USERNAME/toolbox-pro/releases/download/v1.0/磁盘清理工具.exe"
    }
    // 在这里继续添加新兑换码，复制上面一行粘贴修改即可
  },

  // MSI修复工具兑换码
  "msi-fixer": {
    "MSI-DEMO-2024": {
      used: false,
      download: "https://github.com/YOUR_USERNAME/toolbox-pro/releases/download/v1.0/MSI修复工具.exe"
    }
  },

  // 网络重置工具兑换码
  "net-reset": {
    "NET-DEMO-2024": {
      used: false,
      download: "https://github.com/YOUR_USERNAME/toolbox-pro/releases/download/v1.0/网络重置工具.exe"
    }
  },

  // 开机加速工具兑换码
  "startup-manager": {
    "BOOT-DEMO-2024": {
      used: false,
      download: "https://github.com/YOUR_USERNAME/toolbox-pro/releases/download/v1.0/开机加速工具.exe"
    }
  },

  // 图片批量压缩兑换码
  "image-compressor": {
    "IMG-DEMO-2024": {
      used: false,
      download: "https://github.com/YOUR_USERNAME/toolbox-pro/releases/download/v1.0/图片批量压缩工具.exe"
    }
  },

  // 全套工具包兑换码（包含全部工具下载链接）
  "bundle": {
    "BUNDLE-DEMO-2024": {
      used: false,
      download: "https://github.com/YOUR_USERNAME/toolbox-pro/releases/download/v1.0/ToolBoxPro全套工具包.zip"
    }
  }
};
