const state = {
  dashboard: null, catalog: null, movementPage: 1, productPage: 1,
  customerPage: 1, view: 'overview', action: null, editingId: null,
  pickerProduct: null, pickerResults: [], currentDetail: null,
};
const $ = (selector) => document.querySelector(selector);
const money = (cents) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(cents || 0) / 100);
const compactMoney = (cents) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', notation: 'compact', maximumFractionDigits: 1 }).format(Number(cents || 0) / 100);
const number = (value) => new Intl.NumberFormat('pt-BR').format(Number(value || 0));
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const day = (value) => value ? new Date(`${value}T12:00:00`).toLocaleDateString('pt-BR') : 'Sem validade';
const dateTime = (value) => value ? new Date(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';

async function api(path, options) {
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Não foi possível concluir a operação.');
  return result;
}

function toast(message, error = false) {
  const element = $('#toast');
  element.textContent = message;
  element.className = `show${error ? ' error' : ''}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { element.className = ''; }, 4500);
}

async function loadDashboard() {
  try {
    state.dashboard = await api('/api/dashboard');
    renderDashboard();
    $('#connection-label').textContent = 'Sincronizado';
    $('#data-status').textContent = `Atualizado às ${new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' }).format(new Date())}`;
  } catch (error) {
    $('#connection-label').textContent = 'Sem conexão';
    $('#data-status').textContent = 'Não foi possível atualizar';
    toast(error.message, true);
  }
}

function renderDashboard() {
  const { metrics, trend, category_totals, recent, alert_products, batches } = state.dashboard;
  $('#metric-value').textContent = money(metrics.stock_value_cents);
  $('#metric-risk').textContent = number(metrics.products_at_risk);
  $('#metric-expiring').textContent = number(metrics.expiring_lots_7d);
  $('#metric-revenue').textContent = money(metrics.revenue_7d_cents);
  $('#scale-customers').textContent = number(metrics.customers);
  $('#scale-sales').textContent = number(metrics.sales);
  $('#scale-products').textContent = number(metrics.products);
  $('#hero-scale').textContent = number(metrics.customers);
  $('#chart-total').textContent = money(metrics.revenue_7d_cents);
  $('#mix-total').textContent = compactMoney(metrics.stock_value_cents);
  $('#mix-total').title = money(metrics.stock_value_cents);
  $('#side-title').textContent = metrics.products_at_risk ? `${number(metrics.products_at_risk)} produtos para repor` : 'Estoque acompanhado';
  $('#side-copy').textContent = metrics.products_at_risk ? 'Abra Produtos para ver as prioridades e registrar uma entrada.' : 'Acompanhe as entradas, vendas e perdas do dia.';
  renderChart(trend);
  renderMix(category_totals);
  renderAlerts(alert_products, batches);
  renderRecent(recent);
}

function renderChart(trend) {
  const byDay = Object.fromEntries(trend.map((row) => [row.day, row.revenue_cents]));
  const today = new Date();
  const days = Array.from({ length: 7 }, (_, i) => {
    const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 6 + i);
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    return { label: new Intl.DateTimeFormat('pt-BR', { weekday: 'short' }).format(date).replace('.', ''), value: byDay[key] || 0 };
  });
  const max = Math.max(1, ...days.map((item) => item.value));
  $('#sales-chart').innerHTML = days.map((item, index) => `<div class="bar-item ${index === 6 ? 'today' : ''}" title="${esc(money(item.value))}"><div class="bar-track"><span class="bar" style="height:${Math.max(3, Math.round(item.value / max * 100))}%"></span></div><b>${esc(item.label)}</b></div>`).join('');
}

function renderMix(categories) {
  const active = categories.filter((item) => item.value_cents > 0);
  const total = active.reduce((sum, item) => sum + item.value_cents, 0);
  let start = 0;
  const arcs = active.map((item) => {
    const end = start + item.value_cents / total * 100;
    const arc = `${item.color} ${start.toFixed(1)}% ${end.toFixed(1)}%`;
    start = end;
    return arc;
  });
  $('#mix-donut').style.background = total ? `conic-gradient(${arcs.join(',')})` : '#edf2e8';
  $('#mix-legend').innerHTML = categories.map((item) => `<div class="legend-row"><span><i style="background:${esc(item.color)}"></i>${esc(item.name)}</span><b>${esc(money(item.value_cents))}</b></div>`).join('');
}

function renderAlerts(products, batches) {
  const alerts = products.slice(0, 2).map((product) => ({
    kind: 'low', icon: '!', title: `${product.name} precisa de reposição`,
    detail: `${number(product.stock)} ${product.unit} disponíveis. Sugestão: receber ${number(product.reorder_quantity)} ${product.unit}.`,
    action: 'receipt', id: product.id, label: 'Registrar entrada ↗',
  }));
  const expiry = batches.find((batch) => batch.expires_on);
  if (expiry) alerts.push({ kind: 'expiry', icon: '◷', title: `${expiry.product} perto da validade`, detail: `Lote #${expiry.id}: ${number(expiry.available_quantity)} unidades. Vence ${day(expiry.expires_on)}.`, action: 'sale', id: expiry.product_id, label: 'Registrar venda ↗' });
  $('#alerts').innerHTML = alerts.map((item) => `<article class="alert-card"><span class="alert-icon ${item.kind}">${item.icon}</span><div><strong>${esc(item.title)}</strong><p>${esc(item.detail)}</p><button data-action="${item.action}" data-product="${item.id}">${esc(item.label)}</button></div></article>`).join('') || '<div class="alert-card"><span class="alert-icon">✓</span><div><strong>Sem prioridades urgentes</strong><p>Continue registrando as movimentações para manter o saldo atualizado.</p></div></div>';
}

function renderRecent(recent) {
  $('#movement-list').innerHTML = recent.map((item) => {
    const label = { ENTRY: 'Entrada', SALE: 'Venda', LOSS: 'Perda' }[item.kind];
    const sign = item.kind === 'ENTRY' ? '+' : '−';
    return `<div class="movement ${item.kind.toLowerCase()}"><span class="movement-icon">${sign}</span><div><strong>${esc(label)} · ${esc(item.product)}</strong><small>${esc(item.detail || '')} · ${esc(dateTime(item.at))}</small></div><b>${sign}${number(item.quantity)}</b></div>`;
  }).join('') || '<p class="muted">Nenhuma movimentação recente.</p>';
}

const viewInfo = {
  overview: ['Visão geral', 'Acompanhe os indicadores e prioridades do dia.'],
  products: ['Produtos', 'Consulte saldos, cadastros e lotes.'],
  movements: ['Movimentações', 'Confira entradas, vendas e perdas.'],
  customers: ['Clientes', 'Consulte clientes e compras registradas.'],
};
function setView(view) {
  if (!viewInfo[view]) view = 'overview';
  state.view = view;
  document.querySelectorAll('.view').forEach((element) => { element.hidden = element.id !== `view-${view}`; });
  document.querySelectorAll('.nav-item').forEach((element) => { element.classList.toggle('active', element.dataset.view === view); });
  $('#page-title').textContent = viewInfo[view][0];
  $('#page-subtitle').textContent = viewInfo[view][1];
  if (view === 'products') loadProducts();
  if (view === 'movements') loadMovements();
  if (view === 'customers' && $('#customer-directory-search').value.trim().length >= 2) loadCustomers();
  window.scrollTo({ top: 0, behavior: 'instant' });
}

async function loadProducts() {
  const requestId = loadProducts.requestId = (loadProducts.requestId || 0) + 1;
  $('#product-rows').innerHTML = '<tr><td colspan="6" class="loading">Carregando produtos...</td></tr>';
  const query = encodeURIComponent($('#search').value.trim());
  const filter = encodeURIComponent($('#filter').value);
  const requestedPage = state.productPage;
  try {
    const page = await api(`/api/products?page=${requestedPage}&q=${query}&filter=${filter}`);
    if (requestId !== loadProducts.requestId || query !== encodeURIComponent($('#search').value.trim()) || filter !== encodeURIComponent($('#filter').value) || requestedPage !== state.productPage) return;
    if (page.page > page.pages) { state.productPage = page.pages; return loadProducts(); }
    state.catalog = page;
    $('#product-rows').innerHTML = page.items.map((product) => {
      const label = { ok: 'Em dia', low: 'Repor agora', out: 'Sem estoque', inactive: 'Inativo' }[product.alert];
      const coverage = product.coverage_days === null ? 'Sem histórico' : `${number(product.coverage_days)} dias`;
      return `<tr><td><button class="product-link" data-detail-product="${product.id}"><span class="product-icon">▣</span><span><strong>${esc(product.name)}</strong><small>${esc(product.sku)} · #${product.id}</small></span></button></td><td>${esc(product.category)}</td><td><span class="stock-number">${number(product.stock)}</span> <span class="muted">${esc(product.unit)}</span></td><td>${esc(coverage)}</td><td><span class="status ${esc(product.alert)}">● ${esc(label)}</span></td><td><div class="row-actions"><button data-detail-product="${product.id}">Detalhes</button><button data-action="receipt" data-product="${product.id}">Entrada</button><button data-action="sale" data-product="${product.id}" ${product.active ? '' : 'disabled'}>Venda</button></div></td></tr>`;
    }).join('') || '<tr><td colspan="6" class="loading">Nenhum produto encontrado. Ajuste a busca ou o filtro.</td></tr>';
    $('#table-count').textContent = `${number(page.total)} produtos encontrados`;
    pagination('products', page);
  } catch (error) { $('#product-rows').innerHTML = `<tr><td colspan="6" class="loading">${esc(error.message)}</td></tr>`; }
}

async function loadMovements() {
  const requestId = loadMovements.requestId = (loadMovements.requestId || 0) + 1;
  $('#movement-rows').innerHTML = '<tr><td colspan="6" class="loading">Carregando movimentações...</td></tr>';
  const kind = $('#movement-filter').value;
  const requestedPage = state.movementPage;
  try {
    const page = await api(`/api/movements?page=${requestedPage}&kind=${encodeURIComponent(kind)}`);
    if (requestId !== loadMovements.requestId || kind !== $('#movement-filter').value || requestedPage !== state.movementPage) return;
    $('#movement-rows').innerHTML = page.items.map((item) => {
      const label = { ENTRY: 'Entrada', SALE: 'Venda', LOSS: 'Perda' }[item.kind];
      const context = item.kind === 'SALE' ? item.customer || 'Venda sem cliente' : item.reason || '—';
      return `<tr><td><strong>${esc(label)}</strong><small class="table-sub">Registro #${item.id}${item.sale_id ? ` · Venda #${item.sale_id}` : ''}</small></td><td><button class="text-button" data-detail-product="${item.product_id}">${esc(item.product)}</button><small class="table-sub">${esc(item.sku)}</small></td><td>#${item.batch_id}</td><td>${esc(context)}</td><td><strong>${item.kind === 'ENTRY' ? '+' : '−'}${number(item.quantity)}</strong></td><td>${esc(dateTime(item.at))}</td></tr>`;
    }).join('') || '<tr><td colspan="6" class="loading">Nenhuma movimentação encontrada.</td></tr>';
    $('#movement-count').textContent = `${number(page.total)} movimentações`;
    pagination('movements', page);
  } catch (error) { $('#movement-rows').innerHTML = `<tr><td colspan="6" class="loading">${esc(error.message)}</td></tr>`; }
}

async function loadCustomers() {
  const requestId = loadCustomers.requestId = (loadCustomers.requestId || 0) + 1;
  const query = $('#customer-directory-search').value.trim();
  const requestedPage = state.customerPage;
  if (query.length < 2) {
    $('#customer-directory').innerHTML = '<div class="empty-state">Digite pelo menos 2 caracteres para buscar.</div>';
    $('#customer-count').textContent = '';
    pagination('customers', { page: 1, pages: 1 });
    return;
  }
  $('#customer-directory').innerHTML = '<div class="empty-state">Buscando clientes...</div>';
  try {
    const page = await api(`/api/customers?page=${requestedPage}&q=${encodeURIComponent(query)}`);
    if (requestId !== loadCustomers.requestId || $('#customer-directory-search').value.trim() !== query || requestedPage !== state.customerPage) return;
    $('#customer-directory').innerHTML = page.items.map((customer) => `<button class="customer-card" data-detail-customer="${customer.id}"><span class="customer-avatar">${esc(customer.name.charAt(0))}</span><span><strong>${esc(customer.name)}</strong><small>${esc(customer.code)} · Cliente #${customer.id}</small></span><span class="customer-arrow">↗</span></button>`).join('') || '<div class="empty-state">Nenhum cliente encontrado.</div>';
    $('#customer-count').textContent = `${number(page.total)} clientes encontrados`;
    pagination('customers', page);
  } catch (error) { $('#customer-directory').innerHTML = `<div class="empty-state">${esc(error.message)}</div>`; }
}

function pagination(prefix, page) {
  $(`#${prefix}-page`).textContent = `Página ${number(page.page)} de ${number(page.pages)}`;
  $(`#${prefix}-prev`).disabled = page.page <= 1;
  $(`#${prefix}-next`).disabled = page.page >= page.pages;
}

const field = (label, name, input, hint = '') => `<label class="field">${label}${input.replace('NAME', `name="${name}"`)}${hint ? `<small>${esc(hint)}</small>` : ''}</label>`;
const options = (items, selected) => items.map((item) => `<option value="${item.id}" ${Number(selected) === item.id ? 'selected' : ''}>${esc(item.name)}</option>`).join('');
const unitOptions = (selected) => [['un', 'Unidade'], ['pct', 'Pacote'], ['cx', 'Caixa']].map(([value, label]) => `<option value="${value}" ${value === selected ? 'selected' : ''}>${label}</option>`).join('');
function findProduct(id) {
  return state.catalog?.items.find((item) => item.id === Number(id))
    || state.dashboard?.alert_products.find((item) => item.id === Number(id))
    || (state.currentDetail?.product?.id === Number(id) ? state.currentDetail.product : null);
}
function productPicker(product) {
  return `<div class="picker"><label class="field">Produto<input id="product-search" type="search" autocomplete="off" placeholder="Busque pelo nome ou SKU" value="${product ? esc(`${product.name} · ${product.sku}`) : ''}"></label><input type="hidden" name="product_id" id="product-id" value="${product?.id || ''}"><div id="product-results" class="picker-results"></div><small id="selected-product">${product ? `Selecionado: ${esc(product.name)}` : 'Selecione um produto da lista.'}</small></div>`;
}

function openDialog(action, productId = null) {
  if (!state.dashboard) { toast('Aguarde o carregamento dos dados.', true); return; }
  state.action = action;
  state.editingId = action === 'edit' ? Number(productId) : null;
  state.pickerProduct = productId ? findProduct(productId) : null;
  const product = state.pickerProduct;
  const titles = { product: 'Cadastrar produto', edit: 'Editar produto', receipt: 'Registrar entrada', sale: 'Registrar venda', loss: 'Registrar perda' };
  const helps = { product: 'Informe os dados do produto. O número interno será criado automaticamente.', edit: `Produto #${productId}. O número interno é permanente e não pode ser alterado.`, receipt: 'Informe o produto, a quantidade e os dados do lote recebido.', sale: 'Escolha o produto e confira o valor antes de registrar.', loss: 'Informe a quantidade e o motivo para manter o estoque correto.' };
  $('#dialog-title').textContent = titles[action];
  $('#dialog-help').textContent = helps[action];
  $('#submit-dialog').textContent = action === 'product' ? 'Cadastrar produto' : action === 'edit' ? 'Salvar alterações' : 'Confirmar registro';
  const qty = field('Quantidade', 'quantity', '<input NAME type="number" min="1" max="100000" step="1" required placeholder="Ex.: 12">');
  let fields = '';
  if (action === 'product' || action === 'edit') {
    const value = product || {};
    fields = `<div class="form-note">Número interno atribuído automaticamente pelo sistema${action === 'edit' ? ` · #${productId}` : ''}</div>`
      + `<div class="field-row">${field('SKU · código comercial', 'sku', `<input NAME required minlength="3" maxlength="30" value="${esc(value.sku || '')}" placeholder="Ex.: CAF-500">`)}${field('Nome do produto', 'name', `<input NAME required minlength="3" maxlength="80" value="${esc(value.name || '')}" placeholder="Ex.: Café torrado 500 g">`)}</div>`
      + `<div class="field-row">${field('Categoria', 'category_id', `<select NAME required>${options(state.dashboard.categories, value.category_id)}</select>`)}${field('Fornecedor', 'supplier_id', `<select NAME required>${options(state.dashboard.suppliers, value.supplier_id)}</select>`)}</div>`
      + `<div class="field-row">${field('Unidade', 'unit', `<select NAME>${unitOptions(value.unit || 'un')}</select>`)}${field('Estoque mínimo', 'min_stock', `<input NAME type="number" min="0" max="100000" value="${value.min_stock ?? 10}" required>`)}</div>`
      + `<div class="field-row">${field('Prazo de entrega (dias)', 'lead_days', `<input NAME type="number" min="1" max="90" value="${value.lead_days ?? 3}" required>`)}${field('Preço de venda (R$)', 'sale_price', `<input NAME type="number" min="0" step="0.01" value="${value.sale_price_cents !== undefined ? (value.sale_price_cents / 100).toFixed(2) : '9.90'}" required>`)}</div>`
      + field('Situação', 'active', `<select NAME><option value="1" ${value.active !== 0 ? 'selected' : ''}>Ativo</option><option value="0" ${value.active === 0 ? 'selected' : ''}>Inativo</option></select>`);
  } else if (action === 'receipt') {
    fields = productPicker(product) + `<div class="field-row">${qty}${field('Custo unitário (R$)', 'unit_cost', '<input NAME type="number" min="0" step="0.01" placeholder="Ex.: 5,00" required>')}</div>`
      + `<div class="field-row">${field('Validade', 'expires_on', '<input NAME type="date">', 'Deixe vazio se o produto não tiver validade.')}${field('Nota ou referência', 'source_ref', '<input NAME maxlength="80" placeholder="Ex.: NF-1205">', 'Opcional; evita cadastrar a mesma entrada duas vezes.')}</div>`;
  } else if (action === 'sale') {
    fields = productPicker(product) + qty + `<div class="customer-picker">${field('Cliente (opcional)', 'customer_search', '<input NAME id="customer-search" type="search" autocomplete="off" placeholder="Nome ou código do cliente">')}<input type="hidden" name="customer_id" id="customer-id"><div id="customer-results" class="picker-results"></div><small id="selected-customer">Sem cliente selecionado</small></div><div id="sale-preview" class="sale-preview">Selecione um produto para ver o valor.</div>`;
  } else {
    fields = productPicker(product) + qty + field('Motivo da perda', 'reason', '<input NAME required minlength="3" maxlength="120" placeholder="Ex.: embalagem danificada">');
  }
  $('#dialog-fields').innerHTML = fields;
  if ($('#product-search')) $('#product-search').addEventListener('input', searchPickerProducts);
  if ($('#customer-search')) $('#customer-search').addEventListener('input', searchPickerCustomers);
  if (action === 'sale') $('#dialog-fields [name="quantity"]').addEventListener('input', updateSalePreview);
  $('#action-dialog').showModal();
  if (action === 'sale') updateSalePreview();
  $('#dialog-fields input:not([type="hidden"]), #dialog-fields select')?.focus();
}

function searchPickerProducts(event) {
  const input = event.currentTarget;
  clearTimeout(searchPickerProducts.timer);
  state.pickerProduct = null;
  $('#product-id').value = '';
  $('#selected-product').textContent = 'Selecione um produto da lista.';
  if (state.action === 'sale') updateSalePreview();
  const query = input.value.trim();
  if (query.length < 2) { $('#product-results').innerHTML = ''; return; }
  $('#product-results').innerHTML = '<span>Buscando produtos...</span>';
  searchPickerProducts.timer = setTimeout(async () => {
    try {
      const page = await api(`/api/products?q=${encodeURIComponent(query)}`);
      if (!input.isConnected || input.value.trim() !== query) return;
      state.pickerResults = page.items;
      $('#product-results').innerHTML = page.items.map((item) => `<button type="button" class="picker-result" data-pick-product="${item.id}"><span>${esc(item.name)}<small>${esc(item.sku)}</small></span><b>${number(item.stock)} ${esc(item.unit)}</b></button>`).join('') || '<span>Nenhum produto encontrado.</span>';
    } catch { if (input.isConnected) $('#product-results').innerHTML = '<span>Busca indisponível. Tente novamente.</span>'; }
  }, 200);
}

function searchPickerCustomers(event) {
  const input = event.currentTarget;
  clearTimeout(searchPickerCustomers.timer);
  $('#customer-id').value = '';
  $('#selected-customer').textContent = 'Sem cliente selecionado';
  const query = input.value.trim();
  if (query.length < 2) { $('#customer-results').innerHTML = ''; return; }
  $('#customer-results').innerHTML = '<span>Buscando clientes...</span>';
  searchPickerCustomers.timer = setTimeout(async () => {
    try {
      const page = await api(`/api/customers?q=${encodeURIComponent(query)}`);
      if (!input.isConnected || input.value.trim() !== query) return;
      $('#customer-results').innerHTML = page.items.map((item) => `<button type="button" class="picker-result" data-pick-customer="${item.id}" data-label="${esc(item.name)} · ${esc(item.code)}"><span>${esc(item.name)}<small>${esc(item.code)}</small></span></button>`).join('') || '<span>Nenhum cliente encontrado.</span>';
    } catch { if (input.isConnected) $('#customer-results').innerHTML = '<span>Busca indisponível. Tente novamente.</span>'; }
  }, 220);
}

function updateSalePreview() {
  if (state.action !== 'sale') return;
  const product = state.pickerProduct;
  const quantity = Number($('#dialog-fields [name="quantity"]').value || 0);
  if (!product) { $('#sale-preview').textContent = 'Selecione um produto para ver o valor.'; return; }
  const stock = product.stock;
  $('#sale-preview').innerHTML = `<div><span>Preço unitário</span><strong>${money(product.sale_price_cents)}</strong></div><div><span>Total da venda</span><strong>${money(quantity * product.sale_price_cents)}</strong></div><small>${stock === undefined ? '' : `${number(stock)} ${esc(product.unit)} disponíveis`}${stock !== undefined && quantity > stock ? ' · Quantidade acima do estoque' : ''}</small>`;
}

async function submitAction(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  if (!['product', 'edit'].includes(state.action) && !data.product_id) { toast('Selecione um produto da lista.', true); return; }
  if (state.action === 'sale') {
    if (data.customer_search.trim() && !data.customer_id) { toast('Selecione um cliente ou limpe a busca para vender sem cliente.', true); return; }
    delete data.customer_search;
  }
  if (['product', 'edit'].includes(state.action)) { data.sale_price_cents = Math.round(Number(data.sale_price) * 100); delete data.sale_price; }
  if (state.action === 'receipt') { data.unit_cost_cents = Math.round(Number(data.unit_cost) * 100); delete data.unit_cost; }
  const routes = { product: '/api/products', receipt: '/api/receipts', sale: '/api/sales', loss: '/api/losses' };
  const path = state.action === 'edit' ? `/api/products/${state.editingId}` : routes[state.action];
  const button = $('#submit-dialog');
  button.disabled = true;
  try {
    const result = await api(path, { method: state.action === 'edit' ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    $('#action-dialog').close();
    toast(state.action === 'product' ? `Produto cadastrado. Número interno #${result.id} criado.` : state.action === 'edit' ? 'Produto atualizado.' : 'Movimentação registrada.');
    await loadDashboard();
    if (state.view === 'products') await loadProducts();
    if (state.view === 'movements') await loadMovements();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function showProduct(id) {
  $('#detail-kicker').textContent = 'PRODUTO';
  $('#detail-title').textContent = 'Carregando produto...';
  $('#detail-subtitle').textContent = '';
  $('#detail-body').innerHTML = '';
  $('#detail-dialog').showModal();
  try {
    const detail = await api(`/api/products/${id}`);
    state.currentDetail = detail;
    const p = detail.product;
    $('#detail-title').textContent = p.name;
    $('#detail-subtitle').textContent = `${p.sku} · Produto #${p.id}`;
    const stock = detail.batches.reduce((sum, batch) => sum + (!batch.expires_on || batch.expires_on >= new Date().toISOString().slice(0, 10) ? batch.available_quantity : 0), 0);
    $('#detail-body').innerHTML = `<div class="detail-actions"><button class="button button-outline" data-action="edit" data-product="${p.id}">Editar cadastro</button><button class="button button-outline" data-action="receipt" data-product="${p.id}">+ Entrada</button><button class="button button-dark" data-action="sale" data-product="${p.id}" ${p.active ? '' : 'disabled'}>Registrar venda</button></div>
      <div class="detail-grid">${detailField('Número interno', `#${p.id}`)}${detailField('SKU', p.sku)}${detailField('Situação', p.active ? 'Ativo' : 'Inativo')}${detailField('Categoria', p.category)}${detailField('Fornecedor', p.supplier)}${detailField('Unidade', p.unit)}${detailField('Estoque disponível', `${number(stock)} ${p.unit}`)}${detailField('Estoque mínimo', number(p.min_stock))}${detailField('Prazo de entrega', `${p.lead_days} dias`)}${detailField('Preço de venda', money(p.sale_price_cents))}</div>
      <h3>Lotes recebidos</h3><div class="detail-table"><table><thead><tr><th>Lote</th><th>Recebido</th><th>Disponível</th><th>Custo/un.</th><th>Validade</th><th>Referência</th><th>Entrada</th></tr></thead><tbody>${detail.batches.map((b) => `<tr><td>#${b.id}</td><td>${number(b.quantity_received)}</td><td>${number(b.available_quantity)}</td><td>${money(b.unit_cost_cents)}</td><td>${day(b.expires_on)}</td><td>${esc(b.source_ref || '—')}</td><td>${dateTime(b.received_at)}</td></tr>`).join('') || '<tr><td colspan="7">Nenhum lote recebido.</td></tr>'}</tbody></table></div>
      <h3>Baixas recentes</h3><div class="detail-table"><table><thead><tr><th>Registro</th><th>Tipo</th><th>Lote</th><th>Qtd.</th><th>Venda</th><th>Cliente ou motivo</th><th>Data</th></tr></thead><tbody>${detail.events.map((e) => `<tr><td>#${e.id}</td><td>${e.kind === 'SALE' ? 'Venda' : 'Perda'}</td><td>#${e.batch_id}</td><td>${number(e.quantity)}</td><td>${e.sale_id ? `#${e.sale_id}` : '—'}</td><td>${esc(e.customer || e.reason || '—')}</td><td>${dateTime(e.occurred_at)}</td></tr>`).join('') || '<tr><td colspan="7">Nenhuma baixa registrada.</td></tr>'}</tbody></table></div>`;
  } catch (error) { $('#detail-body').innerHTML = `<div class="empty-state">${esc(error.message)}</div>`; }
}

async function showCustomer(id) {
  $('#detail-kicker').textContent = 'CLIENTE';
  $('#detail-title').textContent = 'Carregando cliente...';
  $('#detail-subtitle').textContent = '';
  $('#detail-body').innerHTML = '';
  $('#detail-dialog').showModal();
  try {
    const detail = await api(`/api/customers/${id}`);
    const { customer, summary, sales } = detail;
    $('#detail-title').textContent = customer.name;
    $('#detail-subtitle').textContent = `${customer.code} · Cliente #${customer.id}`;
    $('#detail-body').innerHTML = `<div class="detail-grid">${detailField('Número interno', `#${customer.id}`)}${detailField('Código', customer.code)}${detailField('Compras', number(summary.purchases))}${detailField('Unidades compradas', number(summary.units))}${detailField('Valor das compras', money(summary.revenue_cents))}</div><h3>Compras recentes</h3><div class="detail-table"><table><thead><tr><th>Venda</th><th>Produto</th><th>Quantidade</th><th>Preço/un.</th><th>Total</th><th>Data</th></tr></thead><tbody>${sales.map((sale) => `<tr><td>#${sale.id}</td><td>${esc(sale.product)}</td><td>${number(sale.quantity)}</td><td>${money(sale.unit_price_cents)}</td><td>${money(sale.quantity * sale.unit_price_cents)}</td><td>${dateTime(sale.sold_at)}</td></tr>`).join('') || '<tr><td colspan="6">Nenhuma compra registrada.</td></tr>'}</tbody></table></div>`;
  } catch (error) { $('#detail-body').innerHTML = `<div class="empty-state">${esc(error.message)}</div>`; }
}
const detailField = (label, value) => `<div class="detail-field"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;

document.addEventListener('click', (event) => {
  const productChoice = event.target.closest('[data-pick-product]');
  if (productChoice) {
    state.pickerProduct = state.pickerResults.find((item) => item.id === Number(productChoice.dataset.pickProduct));
    $('#product-id').value = state.pickerProduct.id;
    $('#product-search').value = `${state.pickerProduct.name} · ${state.pickerProduct.sku}`;
    $('#selected-product').textContent = `Selecionado: ${state.pickerProduct.name}`;
    $('#product-results').innerHTML = '';
    updateSalePreview();
    return;
  }
  const customerChoice = event.target.closest('[data-pick-customer]');
  if (customerChoice) {
    $('#customer-id').value = customerChoice.dataset.pickCustomer;
    $('#customer-search').value = customerChoice.dataset.label;
    $('#selected-customer').textContent = `Selecionado: ${customerChoice.dataset.label}`;
    $('#customer-results').innerHTML = '';
    return;
  }
  const productDetail = event.target.closest('[data-detail-product]');
  if (productDetail) { showProduct(productDetail.dataset.detailProduct); return; }
  const customerDetail = event.target.closest('[data-detail-customer]');
  if (customerDetail) { showCustomer(customerDetail.dataset.detailCustomer); return; }
  const action = event.target.closest('[data-action]');
  if (action) {
    if ($('#detail-dialog').open) $('#detail-dialog').close();
    openDialog(action.dataset.action, action.dataset.product || null);
    return;
  }
  const view = event.target.closest('[data-view]');
  if (view) {
    if (window.location.hash.slice(1) === view.dataset.view) setView(view.dataset.view);
    else window.location.hash = view.dataset.view;
  }
});

$('#search').addEventListener('input', () => { clearTimeout(loadProducts.timer); state.productPage = 1; loadProducts.timer = setTimeout(loadProducts, 220); });
$('#filter').addEventListener('change', () => { state.productPage = 1; loadProducts(); });
$('#movement-filter').addEventListener('change', () => { state.movementPage = 1; loadMovements(); });
$('#customer-directory-search').addEventListener('input', () => { clearTimeout(loadCustomers.timer); state.customerPage = 1; loadCustomers.timer = setTimeout(loadCustomers, 220); });
for (const [prefix, load, key] of [['products', loadProducts, 'productPage'], ['movements', loadMovements, 'movementPage'], ['customers', loadCustomers, 'customerPage']]) {
  $(`#${prefix}-prev`).addEventListener('click', () => { state[key]--; load(); });
  $(`#${prefix}-next`).addEventListener('click', () => { state[key]++; load(); });
}
$('#action-form').addEventListener('submit', submitAction);
$('#close-dialog').addEventListener('click', () => $('#action-dialog').close());
$('#cancel-dialog').addEventListener('click', () => $('#action-dialog').close());
$('#close-detail').addEventListener('click', () => $('#detail-dialog').close());
window.addEventListener('hashchange', () => setView(location.hash.slice(1)));
setView(location.hash.slice(1));
loadDashboard();
