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
      download: "https://github.com/lincyang720/toolbox-pro/releases/download/v1.0/disk-cleaner.exe"
    }
  },

  // MSI修复工具兑换码
  "msi-fixer": {
    "MSI-DEMO-2024": {
      used: false,
      download: "https://github.com/lincyang720/toolbox-pro/releases/download/v1.0/msi-fixer.exe"
    }
  },

  // 网络重置工具兑换码
  "net-reset": {
    "NET-DEMO-2024": {
      used: false,
      download: "https://github.com/lincyang720/toolbox-pro/releases/download/v1.0/net-reset.exe"
    }
  },

  // 开机加速工具兑换码
  "startup-manager": {
    "BOOT-DEMO-2024": {
      used: false,
      download: "https://github.com/lincyang720/toolbox-pro/releases/download/v1.0/startup-manager.exe"
    }
  },

  // 图片批量压缩兑换码
  "image-compressor": {
    "IMG-DEMO-2024": {
      used: false,
      download: "https://github.com/lincyang720/toolbox-pro/releases/download/v1.0/image-compressor.exe"
    }
  },

  // SnapTool 截图工具兑换码
  "snaptool": {
    "SNAP-DEMO-2024": {
      used: false,
      download: "https://github.com/lincyang720/toolbox-pro/releases/download/v1.0/snaptool.exe"
    }
  },

  // 全套工具包兑换码
  "bundle": {
    "BUNDLE-DEMO-2024": {
      used: false,
      download: "https://github.com/lincyang720/toolbox-pro/releases/download/v1.0/disk-cleaner.exe"
    }
  }
};
