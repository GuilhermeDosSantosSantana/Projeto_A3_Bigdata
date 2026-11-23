const state = { data: null, action: null, selectedProduct: null };
const $ = (selector) => document.querySelector(selector);
const money = (cents) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format((cents || 0) / 100);
const number = (value) => new Intl.NumberFormat('pt-BR').format(value || 0);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);

function toast(message, error = false) {
  const element = $('#toast');
  element.textContent = message;
  element.className = `show${error ? ' error' : ''}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { element.className = ''; }, 3500);
}

async function load() {
  try {
    const response = await fetch('/api/dashboard', { cache: 'no-store' });
    if (!response.ok) throw new Error('Não foi possível consultar o banco');
    state.data = await response.json();
    render();
  } catch (error) {
    $('#product-rows').innerHTML = '<tr><td colspan="6" class="loading">Falha ao carregar. Atualize a página.</td></tr>';
    toast(error.message, true);
  }
}

function render() {
  const { metrics, products, batches, trend, category_totals, recent } = state.data;
  $('#metric-value').textContent = money(metrics.stock_value_cents);
  $('#metric-risk').textContent = number(metrics.products_at_risk);
  $('#metric-expiring').textContent = number(metrics.expiring_lots_7d);
  $('#metric-revenue').textContent = money(metrics.revenue_7d_cents);
  $('#chart-total').textContent = money(metrics.revenue_7d_cents);
  $('#mix-total').textContent = money(metrics.stock_value_cents);
  renderChart(trend);
  renderMix(category_totals);
  renderAlerts(products, batches);
  renderTable();
  renderRecent(recent);
}

function renderChart(trend) {
  const byDay = Object.fromEntries(trend.map((row) => [row.day, row.revenue_cents]));
  const today = new Date();
  const days = Array.from({ length: 7 }, (_, i) => {
    const day = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 6 + i);
    const key = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
    return { label: new Intl.DateTimeFormat('pt-BR', { weekday: 'short' }).format(day).replace('.', ''), value: byDay[key] || 0 };
  });
  const max = Math.max(1, ...days.map((day) => day.value));
  $('#sales-chart').innerHTML = days.map((day, i) => `<div class="bar-item ${i === 6 ? 'today' : ''}" title="${esc(money(day.value))}"><div class="bar-track"><span class="bar" style="height:${Math.max(3, Math.round(day.value / max * 100))}%"></span></div><b>${esc(day.label)}</b></div>`).join('');
}

function renderMix(categories) {
  const active = categories.filter((category) => category.value_cents > 0);
  const total = active.reduce((sum, category) => sum + category.value_cents, 0);
  let start = 0;
  const arcs = active.map((category) => {
    const end = start + category.value_cents / total * 100;
    const arc = `${category.color} ${start.toFixed(1)}% ${end.toFixed(1)}%`;
    start = end;
    return arc;
  });
  $('#mix-donut').style.background = total ? `conic-gradient(${arcs.join(',')})` : '#edf2e8';
  $('#mix-legend').innerHTML = categories.map((category) => `<div class="legend-row"><span><i style="background:${esc(category.color)}"></i>${esc(category.name)}</span><b>${esc(money(category.value_cents))}</b></div>`).join('');
}

function renderAlerts(products, batches) {
  const alerts = [];
  products.filter((p) => p.alert !== 'ok').sort((a, b) => a.stock - b.stock).forEach((p) => {
    alerts.push({ kind: 'low', icon: '!', title: `${p.name} precisa de reposição`, detail: `${p.alert_reason}. Sugestão: comprar ${p.reorder_quantity} ${p.unit}.`, action: 'receipt', id: p.id, label: 'Registrar entrada ↗' });
  });
  batches.filter((b) => b.expires_on).slice(0, 3).forEach((b) => {
    const days = Math.round((new Date(`${b.expires_on}T12:00:00`) - new Date()) / 86400000);
    if (days >= 0 && days <= 7) alerts.push({ kind: 'expiry', icon: '◷', title: `${b.product} perto da validade`, detail: `Lote #${b.id}: ${b.available_quantity} disponíveis. Vence ${new Date(`${b.expires_on}T12:00:00`).toLocaleDateString('pt-BR')}.`, action: 'sale', id: b.product_id, label: 'Registrar venda ↗' });
  });
  $('#alerts').innerHTML = alerts.slice(0, 3).map((a) => `<article class="alert-card"><span class="alert-icon ${a.kind}">${a.icon}</span><div><strong>${esc(a.title)}</strong><p>${esc(a.detail)}</p><button data-action="${a.action}" data-product="${a.id}">${esc(a.label)}</button></div></article>`).join('') || '<div class="alert-card"><span class="alert-icon">✓</span><div><strong>Tudo em dia</strong><p>Nenhum produto abaixo do ponto de reposição nem lote próximo da validade.</p></div></div>';
}

function renderTable() {
  if (!state.data) return;
  const term = $('#search').value.trim().toLocaleLowerCase('pt-BR');
  const filter = $('#filter').value;
  const products = state.data.products.filter((p) => {
    const matches = `${p.name} ${p.sku}`.toLocaleLowerCase('pt-BR').includes(term);
    return matches && (filter === 'all' || filter === 'risk' && p.alert !== 'ok' || filter === 'expiry' && p.expiring_7d > 0);
  });
  $('#product-rows').innerHTML = products.map((p) => {
    const coverage = p.coverage_days === null ? 'Sem histórico' : `${p.coverage_days} dias`;
    const pct = p.coverage_days === null ? 100 : Math.min(100, Math.max(5, p.coverage_days / 14 * 100));
    const status = p.alert === 'out' ? 'Sem estoque' : p.alert === 'low' ? 'Repor agora' : 'Em dia';
    return `<tr><td><div class="product-cell"><span class="product-icon">▣</span><div><strong>${esc(p.name)}</strong><small>${esc(p.sku)} · ${esc(p.supplier)}</small></div></div></td><td>${esc(p.category)}</td><td><span class="stock-number">${number(p.stock)}</span> <span class="muted">${esc(p.unit)}</span></td><td><div class="coverage"><div class="mini-track"><span style="width:${pct}%"></span></div><span>${esc(coverage)}</span></div></td><td><span class="status ${esc(p.alert)}">● ${status}</span></td><td><div class="row-actions"><button data-action="receipt" data-product="${p.id}">+ Entrada</button><button data-action="sale" data-product="${p.id}">Venda</button><button data-action="loss" data-product="${p.id}">Perda</button></div></td></tr>`;
  }).join('') || '<tr><td colspan="6" class="loading">Nenhum produto encontrado.</td></tr>';
}

function renderRecent(recent) {
  $('#movement-list').innerHTML = recent.map((item) => {
    const kind = item.kind === 'ENTRY' ? 'Entrada' : item.kind === 'SALE' ? 'Venda' : 'Perda';
    const icon = item.kind === 'ENTRY' ? '↙' : item.kind === 'SALE' ? '↗' : '−';
    const css = item.kind.toLowerCase();
    const sign = item.kind === 'ENTRY' ? '+' : '−';
    const at = new Date(`${item.at.replace(' ', 'T')}Z`).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
    return `<div class="movement ${css}"><span class="movement-icon">${icon}</span><div><strong>${esc(kind)} · ${esc(item.product)}</strong><small>${esc(item.detail || '')} · ${esc(at)}</small></div><b>${sign}${number(item.quantity)}</b></div>`;
  }).join('') || '<p class="muted">Ainda não há movimentações.</p>';
}

function options(items, selected, labelKey = 'name') {
  return items.map((item) => `<option value="${item.id}" ${Number(selected) === item.id ? 'selected' : ''}>${esc(item[labelKey])}</option>`).join('');
}

function productOptions(selected) {
  return options(state.data.products, selected);
}

function field(label, name, input) {
  return `<label class="field">${label}${input.replace('NAME', `name="${name}"`)}</label>`;
}

function openDialog(action, selectedProduct = null) {
  if (!state.data) return;
  state.action = action;
  state.selectedProduct = selectedProduct;
  const titles = { product: 'Cadastrar produto', receipt: 'Registrar entrada', sale: 'Registrar venda', loss: 'Registrar perda' };
  const helps = { product: 'O SKU evita duplicidade. Os valores ficam associados ao produto.', receipt: 'Cada entrada cria um lote rastreável. A referência evita duplicidade.', sale: 'A venda consome primeiro os lotes com validade mais próxima.', loss: 'Registre a quantidade e o motivo para manter o saldo confiável.' };
  $('#dialog-title').textContent = titles[action];
  $('#dialog-help').textContent = helps[action];
  $('#submit-dialog').textContent = action === 'product' ? 'Cadastrar' : 'Registrar';
  const productSelect = field('Produto', 'product_id', `<select NAME required>${productOptions(selectedProduct)}</select>`);
  const qty = field('Quantidade', 'quantity', '<input NAME type="number" min="1" max="100000" step="1" required placeholder="Ex.: 12">');
  let fields = '';
  if (action === 'product') {
    fields = field('SKU', 'sku', '<input NAME required minlength="3" maxlength="24" placeholder="Ex.: BOL-009">')
      + field('Nome do produto', 'name', '<input NAME required minlength="3" maxlength="80" placeholder="Ex.: Bolo integral">')
      + `<div class="field-row">${field('Categoria', 'category_id', `<select NAME required>${options(state.data.categories)}</select>`)}${field('Fornecedor', 'supplier_id', `<select NAME required>${options(state.data.suppliers)}</select>`)}</div>`
      + `<div class="field-row">${field('Unidade', 'unit', '<select NAME><option value="un">Unidade</option><option value="pct">Pacote</option><option value="cx">Caixa</option></select>')}${field('Estoque mínimo', 'min_stock', '<input NAME type="number" min="0" max="100000" step="1" value="10" required>')}</div>`
      + `<div class="field-row">${field('Prazo do fornecedor (dias)', 'lead_days', '<input NAME type="number" min="1" max="90" step="1" value="3" required>')}${field('Preço de venda (R$)', 'sale_price', '<input NAME type="number" min="0" step="0.01" value="9.90" required>')}</div>`;
  } else if (action === 'receipt') {
    fields = productSelect + `<div class="field-row">${qty}${field('Custo unitário (R$)', 'unit_cost', '<input NAME type="number" min="0" step="0.01" value="5.00" required>')}</div>`
      + `<div class="field-row">${field('Validade (se houver)', 'expires_on', '<input NAME type="date">')}${field('Nota / referência', 'source_ref', '<input NAME maxlength="80" placeholder="Ex.: NF-1205">')}</div>`;
  } else if (action === 'sale') {
    fields = productSelect + qty;
  } else {
    fields = productSelect + qty + field('Motivo da perda', 'reason', '<input NAME required minlength="3" maxlength="120" placeholder="Ex.: embalagem danificada">');
  }
  $('#dialog-fields').innerHTML = fields;
  $('#action-dialog').showModal();
  $('#dialog-fields input, #dialog-fields select')?.focus();
}

async function submitAction(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form));
  if (state.action === 'product') {
    data.sale_price_cents = Math.round(Number(data.sale_price) * 100);
    delete data.sale_price;
  }
  if (state.action === 'receipt') {
    data.unit_cost_cents = Math.round(Number(data.unit_cost) * 100);
    delete data.unit_cost;
  }
  const path = { product: 'products', receipt: 'receipts', sale: 'sales', loss: 'losses' }[state.action];
  const button = $('#submit-dialog');
  button.disabled = true;
  try {
    const response = await fetch(`/api/${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Não foi possível salvar');
    $('#action-dialog').close();
    toast('Registro salvo no banco com sucesso');
    await load();
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-action]');
  if (button) openDialog(button.dataset.action, button.dataset.product || null);
});
$('#search').addEventListener('input', renderTable);
$('#filter').addEventListener('change', renderTable);
$('#action-form').addEventListener('submit', submitAction);
$('#close-dialog').addEventListener('click', () => $('#action-dialog').close());
$('#cancel-dialog').addEventListener('click', () => $('#action-dialog').close());
$('#today').textContent = `${new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full' }).format(new Date())}. Seu estoque, sem pontos cegos.`;
load();
