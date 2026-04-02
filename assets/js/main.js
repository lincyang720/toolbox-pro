// 生成简单的占位收款码图片（SVG → Canvas → PNG）
// 实际使用时替换为真实收款码图片

function makePlaceholderQR(canvas, label, color) {
  const ctx = canvas.getContext('2d');
  const s = canvas.width;
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, s, s);

  // 模拟二维码格子
  ctx.fillStyle = '#222';
  const cell = 10, cols = Math.floor(s / cell);
  for (let r = 0; r < cols; r++) {
    for (let c = 0; c < cols; c++) {
      if (Math.random() > 0.5 ||
          (r < 7 && c < 7) || (r < 7 && c > cols - 8) || (r > cols - 8 && c < 7)) {
        ctx.fillRect(c * cell, r * cell, cell - 1, cell - 1);
      }
    }
  }

  // 定位角
  [[[1,1],[5,5]], [[cols-6,1],[5,5]], [[1,cols-6],[5,5]]].forEach(([[x,y],[w,h]])=>{
    ctx.fillStyle = '#222';
    ctx.fillRect(x*cell, y*cell, w*cell, h*cell);
    ctx.fillStyle = '#fff';
    ctx.fillRect((x+1)*cell, (y+1)*cell, (w-2)*cell, (h-2)*cell);
    ctx.fillStyle = '#222';
    ctx.fillRect((x+2)*cell, (y+2)*cell, (w-4)*cell, (h-4)*cell);
  });

  // 标签
  ctx.fillStyle = color;
  ctx.font = 'bold 20px Arial';
  ctx.textAlign = 'center';
  ctx.fillText(label, s/2, s - 10);
}

// ── 支付弹窗 ──
let currentProduct = null;

const PRODUCT_INFO = {
  'disk-cleaner':    { name: '磁盘清理工具',   price: '9.9'  },
  'msi-fixer':       { name: 'MSI 修复工具',   price: '6.9'  },
  'net-reset':       { name: '网络重置工具',   price: '6.9'  },
  'startup-manager': { name: '开机加速工具',   price: '8.9'  },
  'image-compressor':{ name: '图片批量压缩',   price: '9.9'  },
  'bundle':          { name: '全套工具包',     price: '29.9' },
};

function openPayModal(productId) {
  currentProduct = productId;
  const modal = document.getElementById('pay-modal');
  modal.classList.add('show');
  setPayStep(1);
  setPayTab('wechat');
  document.getElementById('code-error').classList.remove('show');
  document.getElementById('code-input').value = '';

  // 统一更新价格和标题
  const info = PRODUCT_INFO[productId] || { name: '工具', price: '?' };

  // 更新弹窗标题（如果有的话）
  const titleEl = modal.querySelector('.modal-header h3');
  if (titleEl) titleEl.textContent = `购买 — ${info.name}`;

  // 更新价格显示，兼容两种写法
  const amountEl = document.getElementById('pay-amount');
  const amountValEl = document.getElementById('pay-amount-val');
  if (amountEl)    amountEl.innerHTML    = `¥${info.price} <small>元</small>`;
  if (amountValEl) amountValEl.textContent = info.price;

  // 兜底：直接找 .qr-amount 改
  modal.querySelectorAll('.qr-amount').forEach(el => {
    el.innerHTML = `¥${info.price} <small>元</small>`;
  });

  // 更新支付提示文字，把价格写进去
  const hintEl = modal.querySelector('.pay-hint');
  if (hintEl) {
    hintEl.innerHTML = `扫码时请备注金额 <strong>¥${info.price}</strong>，并截图发给客服<br>微信客服：<strong>newboy2004</strong>`;
  }
}

function closePayModal() {
  document.getElementById('pay-modal').classList.remove('show');
  currentProduct = null;
}

function setPayStep(step) {
  document.querySelectorAll('.pay-step').forEach((el, i) => {
    el.classList.remove('active', 'done');
    if (i + 1 < step) el.classList.add('done');
    if (i + 1 === step) el.classList.add('active');
  });
  document.getElementById('step-pay').style.display  = step === 1 ? 'block' : 'none';
  document.getElementById('step-code').style.display = step === 2 ? 'block' : 'none';
  document.getElementById('step-done').style.display = step === 3 ? 'block' : 'none';
}

function setPayTab(type) {
  document.querySelectorAll('.pay-tab').forEach(el => el.classList.remove('active'));
  document.querySelector(`.pay-tab[data-tab="${type}"]`).classList.add('active');
  document.getElementById('qr-wechat').style.display = type === 'wechat' ? 'block' : 'none';
  document.getElementById('qr-alipay').style.display = type === 'alipay' ? 'block' : 'none';
}

function verifyCode() {
  if (!currentProduct) return;
  const input = document.getElementById('code-input').value.trim().toUpperCase();
  const errEl = document.getElementById('code-error');

  if (!input) {
    errEl.textContent = '请输入兑换码';
    errEl.classList.add('show');
    return;
  }

  const codes = window.CODES?.[currentProduct] || {};
  if (!codes[input]) {
    errEl.textContent = '兑换码无效，请检查是否输入正确';
    errEl.classList.add('show');
    return;
  }
  if (codes[input].used) {
    errEl.textContent = '该兑换码已被使用';
    errEl.classList.add('show');
    return;
  }

  // 验证通过
  errEl.classList.remove('show');
  codes[input].used = true;

  const dlBtn = document.getElementById('download-btn');
  dlBtn.href = codes[input].download;
  setPayStep(3);
}

// ── 点击遮罩关闭弹窗 ──
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('pay-modal').addEventListener('click', function(e) {
    if (e.target === this) closePayModal();
  });

  // ESC 关闭
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closePayModal();
  });
});
