/**
 * Industrial-MCP SCADA Dashboard Frontend Client
 * WebSocket streaming, Highcharts Polar + Spline, and Human-in-the-Loop interaction.
 */

document.addEventListener("DOMContentLoaded", () => {
  let ws = null;
  let polarChart = null;
  let timeSeriesChart = null;
  let activeHitlTicket = null;
  let isPlaying = true;
  let currentSpeed = 1.0;

  // DOM Elements
  const wsBadge = document.getElementById("ws-status-badge");
  const wsText = document.getElementById("ws-status-text");
  const btnTogglePlay = document.getElementById("btn-toggle-play");
  const iconPlayState = document.getElementById("icon-play-state");
  const labelPlayState = document.getElementById("label-play-state");
  const speedButtons = document.querySelectorAll(".btn-speed");

  const btnInjectAngle = document.getElementById("btn-inject-angle");
  const btnInjectPressure = document.getElementById("btn-inject-pressure");

  // KPI elements
  const kpiAngle = document.getElementById("kpi-angle");
  const kpiDirection = document.getElementById("kpi-direction");
  const kpiPressure = document.getElementById("kpi-pressure");
  const barPressure = document.getElementById("bar-pressure");
  const cardPressure = document.getElementById("card-pressure");
  const kpiRunningStatus = document.getElementById("kpi-running-status");
  const dotStatus = document.getElementById("dot-status");
  const kpiWaterMode = document.getElementById("kpi-water-mode");
  const kpiPercentTimer = document.getElementById("kpi-percent-timer");
  const kpiFlowRate = document.getElementById("kpi-flow-rate");
  const polarAngleIndicator = document.getElementById("polar-angle-indicator");

  // Watchdog & MCP elements
  const panelWatchdog = document.getElementById("panel-watchdog");
  const badgeWatchdog = document.getElementById("badge-watchdog-status");
  const watchdogScore = document.getElementById("watchdog-score");
  const watchdogPumpCheck = document.getElementById("watchdog-pump-check");
  const watchdogEncoderCheck = document.getElementById("watchdog-encoder-check");
  const watchdogAlertBox = document.getElementById("watchdog-alert-box");
  const watchdogAlertText = document.getElementById("watchdog-alert-text");
  const mcpLogContainer = document.getElementById("mcp-log-container");

  // Side Drawer Elements
  const drawerAlerts = document.getElementById("drawer-alerts");
  const btnToggleAlerts = document.getElementById("btn-toggle-alerts");
  const btnCloseDrawer = document.getElementById("btn-close-drawer");
  const alertsBadgeCount = document.getElementById("alerts-badge-count");
  const drawerBadgeStatus = document.getElementById("drawer-badge-status");
  const hitlActionCard = document.getElementById("hitl-action-card");
  const alertsHistoryList = document.getElementById("alerts-history-list");
  const hitlTicketId = document.getElementById("hitl-ticket-id");
  const hitlPivotTarget = document.getElementById("hitl-pivot-target");
  const hitlCommandName = document.getElementById("hitl-command-name");
  const hitlReasonText = document.getElementById("hitl-reason-text");
  const btnHitlApprove = document.getElementById("btn-hitl-approve");
  const btnHitlReject = document.getElementById("btn-hitl-reject");

  // Asset Selector DOM elements
  const inputFarmSearch = document.getElementById("input-farm-search");
  const selectFarm = document.getElementById("select-farm");
  const selectEquipType = document.getElementById("select-equip-type");
  const inputEquipSearch = document.getElementById("input-equip-search");
  const selectEquipment = document.getElementById("select-equipment");
  const btnApplyEquipment = document.getElementById("btn-apply-equipment");

  const badgeActiveEquip = document.getElementById("badge-active-equip");
  const badgeActiveMaker = document.getElementById("badge-active-maker");
  const badgeActiveRadius = document.getElementById("badge-active-radius");
  const badgeActivePressure = document.getElementById("badge-active-pressure");

  const headerFarmName = document.getElementById("header-farm-name");
  const headerPivotName = document.getElementById("header-pivot-name");

  // -------------------------------------------------------------------------
  // 1. Initialize Highcharts Charts
  // -------------------------------------------------------------------------

  function initHighcharts() {
    Highcharts.setOptions({
      chart: {
        backgroundColor: "transparent",
        style: { fontFamily: "'Plus Jakarta Sans', sans-serif" }
      },
      credits: { enabled: false }
    });

    // Polar 360° Pivot Geometry Chart
    polarChart = Highcharts.chart("container-polar", {
      chart: {
        polar: true,
        type: "line",
        animation: { duration: 250 }
      },
      title: { text: null },
      pane: {
        startAngle: 0,
        endAngle: 360,
        background: [
          {
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            borderWidth: 1,
            borderColor: "rgba(51, 65, 85, 0.6)"
          }
        ]
      },
      xAxis: {
        min: 0,
        max: 360,
        tickInterval: 45,
        gridLineColor: "rgba(51, 65, 85, 0.5)",
        labels: {
          style: { color: "#94a3b8", fontSize: "11px", fontWeight: "600" },
          formatter: function () {
            return this.value + "°";
          }
        }
      },
      yAxis: {
        min: 0,
        max: 400,
        tickInterval: 100,
        gridLineColor: "rgba(51, 65, 85, 0.4)",
        labels: {
          style: { color: "#64748b", fontSize: "10px" },
          formatter: function () {
            return this.value + "m";
          }
        }
      },
      plotOptions: {
        series: {
          enableMouseTracking: true,
          marker: { enabled: true, radius: 4 }
        }
      },
      legend: { enabled: false },
      series: [
        {
          name: "Braço do Pivô",
          data: [[0, 0], [0, 380]],
          color: "#10b981",
          lineWidth: 3.5,
          marker: {
            fillColor: "#34d399",
            lineWidth: 2,
            lineColor: "#059669",
            radius: 5
          }
        },
        {
          type: "area",
          name: "Setor de Varredura",
          data: [[0, 380], [0, 0]],
          color: "rgba(16, 185, 129, 0.15)",
          lineWidth: 0,
          enableMouseTracking: false
        }
      ]
    });

    // Real-Time Spline Time-Series Chart
    timeSeriesChart = Highcharts.chart("container-timeseries", {
      chart: {
        type: "spline",
        animation: false
      },
      title: { text: null },
      xAxis: {
        type: "category",
        gridLineColor: "rgba(51, 65, 85, 0.3)",
        labels: { style: { color: "#64748b", fontSize: "10px" } }
      },
      yAxis: [
        {
          title: {
            text: "Pressão (bar)",
            style: { color: "#10b981", fontSize: "11px", fontWeight: "600" }
          },
          min: 0,
          max: 5,
          gridLineColor: "rgba(51, 65, 85, 0.4)",
          labels: { style: { color: "#10b981", fontSize: "10px" } }
        },
        {
          title: {
            text: "Percentímetro (%)",
            style: { color: "#f59e0b", fontSize: "11px", fontWeight: "600" }
          },
          opposite: true,
          min: 0,
          max: 100,
          gridLineColor: "transparent",
          labels: { style: { color: "#f59e0b", fontSize: "10px" } }
        }
      ],
      tooltip: {
        shared: true,
        backgroundColor: "rgba(15, 23, 42, 0.95)",
        borderColor: "#334155",
        style: { color: "#f8fafc", fontSize: "12px" }
      },
      legend: { enabled: false },
      series: [
        {
          name: "Pressão de Base",
          yAxis: 0,
          color: "#10b981",
          lineWidth: 2.5,
          data: []
        },
        {
          name: "Percentímetro CLP",
          yAxis: 1,
          color: "#f59e0b",
          lineWidth: 2,
          data: []
        }
      ]
    });
  }

  // -------------------------------------------------------------------------
  // 2. WebSocket Connection & Stream Consumption
  // -------------------------------------------------------------------------

  function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      wsBadge.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      wsText.textContent = "Ao Vivo (WebSocket)";
      addMcpLog("[WS] Conexão bidirecional estabelecida com sucesso.");
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleTelemetryUpdate(payload);
      } catch (e) {
        console.error("Erro ao decodificar telemetria:", e);
      }
    };

    ws.onclose = () => {
      wsBadge.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20";
      wsText.textContent = "Desconectado (Reconectando...)";
      setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = (err) => {
      console.warn("WebSocket error:", err);
      ws.close();
    };
  }

  // -------------------------------------------------------------------------
  // 3. UI Update Logic for Telemetry & Machine State
  // -------------------------------------------------------------------------

  function handleTelemetryUpdate(data) {
    const tel = data.telemetry;
    const anom = data.anomaly;
    const ticket = data.hitl_ticket;

    if (!tel) return;

    // Sync Playback button state
    isPlaying = data.is_playing;
    currentSpeed = data.speed;
    updatePlaybackControls();

    // 0. Update Header & Active Asset Badges
    if (headerFarmName && tel.farm_name) {
      headerFarmName.textContent = `Fazenda ${tel.farm_name}`;
    }
    if (headerPivotName && tel.pivot_name) {
      const maker = tel.pivot_maker || "Valmont";
      const model = tel.pivot_model || "";
      headerPivotName.textContent = `${tel.pivot_name} (${maker} ${model})`.trim();
    }
    if (badgeActiveEquip && tel.pivot_name) {
      badgeActiveEquip.textContent = `${tel.pivot_name} (#${tel.id_equip})`;
    }
    if (badgeActiveMaker) {
      badgeActiveMaker.textContent = `${tel.pivot_maker || "Valmont"} ${tel.pivot_model || ""}`.trim();
    }
    if (badgeActiveRadius && tel.pivot_radius) {
      badgeActiveRadius.textContent = `${tel.pivot_radius.toFixed(0)} m`;
    }
    if (badgeActivePressure && tel.nominal_pressure) {
      badgeActivePressure.textContent = `${tel.nominal_pressure.toFixed(2)} bar`;
    }

    // 1. Update KPI Values
    const angle = tel.current_angle.toFixed(1);
    kpiAngle.textContent = `${angle}°`;
    kpiDirection.textContent = tel.direction || "Forward";
    polarAngleIndicator.textContent = `${angle}°`;

    kpiPressure.textContent = `${tel.pressure_begin.toFixed(2)} bar`;
    const pressurePct = Math.min(100, Math.max(0, (tel.pressure_begin / 4.0) * 100));
    barPressure.style.width = `${pressurePct}%`;

    // Pressure Bar Colors
    if (tel.pressure_begin < 1.2 && tel.water_mode.toLowerCase() === "wet") {
      barPressure.className = "bg-red-500 h-full rounded-full transition-all duration-300";
      cardPressure.classList.add("border-red-500/50");
    } else {
      barPressure.className = "bg-emerald-500 h-full rounded-full transition-all duration-300";
      cardPressure.classList.remove("border-red-500/50");
    }

    kpiRunningStatus.textContent = tel.running_status.toUpperCase();
    if (tel.running_status.toLowerCase() === "running") {
      dotStatus.className = "w-3 h-3 rounded-full bg-emerald-500 animate-pulse";
      kpiRunningStatus.className = "text-xl font-bold font-mono text-emerald-400";
    } else {
      dotStatus.className = "w-3 h-3 rounded-full bg-red-500";
      kpiRunningStatus.className = "text-xl font-bold font-mono text-red-400";
    }

    kpiWaterMode.textContent = tel.water_mode.toUpperCase();
    kpiPercentTimer.textContent = `${tel.percent_timer.toFixed(1)}%`;
    kpiFlowRate.textContent = `${tel.flow_rate.toFixed(0)} m³/h`;

    // 2. Update Polar Highcharts
    if (polarChart && polarChart.series && polarChart.series[0]) {
      const armLength = tel.pivot_radius || 380;

      // Dynamically auto-scale radius axis
      if (polarChart.yAxis && polarChart.yAxis[0]) {
        const currentMax = polarChart.yAxis[0].max;
        const targetMax = Math.max(50, Math.ceil((armLength * 1.15) / 25) * 25);
        if (Math.abs(currentMax - targetMax) > 15) {
          polarChart.yAxis[0].setExtremes(0, targetMax, false);
        }
      }

      polarChart.series[0].setData([[0, 0], [tel.current_angle, armLength]], true, false);

      // Sector swath representation
      if (polarChart.series[1]) {
        const sweepAngle = Math.max(0, tel.current_angle - 25);
        polarChart.series[1].setData([
          [sweepAngle, armLength],
          [tel.current_angle, armLength],
          [tel.current_angle, 0],
          [sweepAngle, 0]
        ], true, false);
      }
    }

    // 3. Update Spline Time-Series
    if (timeSeriesChart && timeSeriesChart.series) {
      const timeLabel = new Date().toLocaleTimeString();
      const shift = timeSeriesChart.series[0].data.length > 25;
      timeSeriesChart.series[0].addPoint([timeLabel, tel.pressure_begin], false, shift);
      timeSeriesChart.series[1].addPoint([timeLabel, tel.percent_timer], true, shift);
    }

    // 4. Update Watchdog & ML State
    if (anom && anom.is_anomaly) {
      panelWatchdog.classList.add("scada-alert-glow", "border-red-500/60");
      badgeWatchdog.className = "px-2.5 py-1 rounded text-xs font-semibold bg-red-500/20 text-red-300 border border-red-500/40 flex items-center gap-1.5 animate-pulse";
      badgeWatchdog.innerHTML = '<i data-lucide="alert-octagon" class="w-3.5 h-3.5"></i><span>Anomalia Detectada</span>';

      watchdogScore.textContent = `${anom.details?.decision_score ?? -0.32} (Anômalo)`;
      watchdogScore.className = "font-mono font-bold text-red-400";

      watchdogAlertBox.classList.remove("hidden");
      watchdogAlertText.innerHTML = anom.anomaly_types.join("<br/>");

      // Check specific domain checks
      if (anom.anomaly_types.some(t => t.includes("Bomba acionada"))) {
        watchdogPumpCheck.textContent = "FALHA: Pressão Incongruente com Bomba ON";
        watchdogPumpCheck.className = "font-semibold text-red-400";
      }
      if (anom.anomaly_types.some(t => t.includes("Salto anômalo"))) {
        watchdogEncoderCheck.textContent = "FALHA: Salto Angular Impossível no Encoder";
        watchdogEncoderCheck.className = "font-semibold text-red-400";
      }

      addMcpLog(`[WATCHDOG ALARM] Confiança: ${(anom.confidence_score * 100).toFixed(1)}% | Ação: ${anom.recommended_action || "Intervenção sugerida"}`);
    } else {
      panelWatchdog.classList.remove("scada-alert-glow", "border-red-500/60");
      badgeWatchdog.className = "px-2.5 py-1 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5";
      badgeWatchdog.innerHTML = '<i data-lucide="shield-check" class="w-3.5 h-3.5"></i><span>Nominal</span>';

      watchdogScore.textContent = `${anom?.details?.decision_score ?? "+0.284"} (Normal)`;
      watchdogScore.className = "font-mono font-bold text-emerald-400";

      watchdogPumpCheck.textContent = "Aprovado (P > 1.2 bar)";
      watchdogPumpCheck.className = "font-semibold text-emerald-400";
      watchdogEncoderCheck.textContent = "Aprovado (< 6.0°/min)";
      watchdogEncoderCheck.className = "font-semibold text-emerald-400";

      watchdogAlertBox.classList.add("hidden");
    }

    // 5. Handle Human-in-the-Loop (HITL) Alert in Side Drawer
    if (ticket && ticket.status === "AWAITING_OPERATOR_APPROVAL") {
      activeHitlTicket = ticket;
      showHitlAlert(ticket);
    } else if (!ticket && hitlActionCard && !hitlActionCard.classList.contains("hidden")) {
      clearHitlAlert();
    }

    if (window.lucide) {
      lucide.createIcons();
    }
  }

  // -------------------------------------------------------------------------
  // 4. Side Drawer & Human-in-the-Loop (HITL) Alert Actions
  // -------------------------------------------------------------------------

  function openDrawer() {
    if (drawerAlerts) {
      drawerAlerts.classList.remove("translate-x-full");
    }
  }

  function closeDrawer() {
    if (drawerAlerts) {
      drawerAlerts.classList.add("translate-x-full");
    }
  }

  if (btnToggleAlerts) {
    btnToggleAlerts.addEventListener("click", () => {
      if (drawerAlerts && drawerAlerts.classList.contains("translate-x-full")) {
        openDrawer();
      } else {
        closeDrawer();
      }
    });
  }

  if (btnCloseDrawer) {
    btnCloseDrawer.addEventListener("click", closeDrawer);
  }

  function showHitlAlert(ticket) {
    hitlTicketId.textContent = ticket.ticket_id;
    hitlPivotTarget.textContent = `${ticket.pivot_name} (#${ticket.pivot_id})`;
    hitlCommandName.textContent = ticket.action_required || "PARADA DE EMERGÊNCIA";
    hitlReasonText.textContent = ticket.reasons?.join("; ") || "Anomalia severa de pressão e cavitação.";

    hitlActionCard.classList.remove("hidden");

    // Update alert badges
    alertsBadgeCount.textContent = "1";
    alertsBadgeCount.classList.remove("hidden");
    drawerBadgeStatus.textContent = "1 Alerta Crítico";
    drawerBadgeStatus.className = "px-2 py-0.5 rounded text-[11px] font-bold bg-red-500/20 text-red-300 border border-red-500/30 animate-pulse";

    // Append to history list if not already present
    const existing = document.getElementById(`history-${ticket.ticket_id}`);
    if (!existing) {
      const timeStr = new Date().toLocaleTimeString();
      const itemDiv = document.createElement("div");
      itemDiv.id = `history-${ticket.ticket_id}`;
      itemDiv.className = "bg-red-950/40 border border-red-500/40 rounded-xl p-3 text-red-200 space-y-1";
      itemDiv.innerHTML = `
        <div class="flex items-center justify-between font-bold text-red-400">
          <span class="flex items-center gap-1.5"><i data-lucide="alert-octagon" class="w-3.5 h-3.5"></i> ${ticket.action_required || "Intervenção Solicitada"}</span>
          <span class="text-[10px] text-slate-400 font-mono">${timeStr}</span>
        </div>
        <p class="text-[11px] text-red-300/90">${ticket.reasons?.join("; ") || "Anomalia detectada"}</p>
      `;
      alertsHistoryList.prepend(itemDiv);
      if (window.lucide) lucide.createIcons();
    }

    // Slide drawer in gently on the right
    openDrawer();
    addMcpLog(`[HITL GATE] Ticket gerado: ${ticket.ticket_id} no painel lateral.`);
  }

  function clearHitlAlert() {
    hitlActionCard.classList.add("hidden");
    alertsBadgeCount.classList.add("hidden");
    drawerBadgeStatus.textContent = "Nominal";
    drawerBadgeStatus.className = "px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    activeHitlTicket = null;
  }

  btnHitlApprove.addEventListener("click", () => {
    if (!activeHitlTicket) return;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        action: "approve_hitl",
        ticket_id: activeHitlTicket.ticket_id
      }));
    }
    addMcpLog(`[HITL APPROVED] Operador confirmou desarme da bomba para ${activeHitlTicket.ticket_id}. Sinal transmitido ao CLP.`);
    clearHitlAlert();
  });

  btnHitlReject.addEventListener("click", () => {
    if (!activeHitlTicket) return;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        action: "reject_hitl",
        ticket_id: activeHitlTicket.ticket_id
      }));
    }
    addMcpLog(`[HITL DISMISSED] Operador dispensou o alerta.`);
    clearHitlAlert();
  });

  // -------------------------------------------------------------------------
  // 5. Controls & Anomaly Injections
  // -------------------------------------------------------------------------

  function updatePlaybackControls() {
    if (isPlaying) {
      labelPlayState.textContent = "Pausar";
      iconPlayState.setAttribute("data-lucide", "pause");
      btnTogglePlay.className = "flex items-center space-x-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-3 py-1.5 rounded-md transition shadow-sm";
    } else {
      labelPlayState.textContent = "Retomar";
      iconPlayState.setAttribute("data-lucide", "play");
      btnTogglePlay.className = "flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-3 py-1.5 rounded-md transition shadow-sm";
    }
  }

  btnTogglePlay.addEventListener("click", () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: "toggle_play" }));
    }
  });

  speedButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const speed = parseFloat(btn.dataset.speed);
      speedButtons.forEach(b => b.className = "btn-speed px-2.5 py-1 rounded text-slate-300 hover:bg-slate-700 transition");
      btn.className = "btn-speed px-2.5 py-1 rounded bg-slate-700 text-white font-bold transition";
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: "set_speed", speed: speed }));
      }
      addMcpLog(`[CONTROL] Velocidade do stream ajustada para ${speed}x.`);
    });
  });

  btnInjectAngle.addEventListener("click", () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: "inject_anomaly", type: "angle_jump" }));
    }
    addMcpLog("[DEMO GATILHO] Injetado: Salto Angular (+45° no encoder). Watchdog deve acusar salto impossível.");
  });

  btnInjectPressure.addEventListener("click", () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: "inject_anomaly", type: "pressure_drop" }));
    }
    addMcpLog("[DEMO GATILHO] Injetado: Queda de Pressão (0.35 bar com Bomba ON). Acionando HITL de emergência.");
  });

  function addMcpLog(msg) {
    const time = new Date().toLocaleTimeString();
    const div = document.createElement("div");
    div.className = "text-slate-300 leading-relaxed";
    div.textContent = `[${time}] ${msg}`;
    mcpLogContainer.appendChild(div);
    mcpLogContainer.scrollTop = mcpLogContainer.scrollHeight;
  }

  // -------------------------------------------------------------------------
  // 6. Dynamic Asset Catalog & Equipment Switching
  // -------------------------------------------------------------------------

  let currentSelectedFarmId = 1515; // VB Homestead default
  let currentActiveEquipId = 14863;  // Haak 1 default

  function debounce(func, wait = 300) {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  async function fetchFarms(searchQuery = "") {
    try {
      const res = await fetch(`/api/catalog/farms?q=${encodeURIComponent(searchQuery)}&limit=100`);
      if (!res.ok) return;
      const farms = await res.json();

      if (!selectFarm) return;
      selectFarm.innerHTML = "";
      if (farms.length === 0) {
        selectFarm.innerHTML = '<option value="">Nenhuma fazenda encontrada</option>';
        return;
      }

      farms.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f.farm_id;
        const location = f.farm_city ? `${f.farm_city}${f.farm_state ? ", " + f.farm_state : ""}` : "";
        const locTxt = location ? ` - ${location}` : "";
        opt.textContent = `${f.farm_name} (${f.total_equips} equips)${locTxt}`;
        if (f.farm_id === currentSelectedFarmId) {
          opt.selected = true;
        }
        selectFarm.appendChild(opt);
      });

      if (!selectFarm.value && farms.length > 0) {
        selectFarm.value = farms[0].farm_id;
      }
      currentSelectedFarmId = parseInt(selectFarm.value);
    } catch (err) {
      console.error("Erro ao carregar fazendas:", err);
    }
  }

  async function fetchEquipment() {
    try {
      const farmId = selectFarm ? selectFarm.value : "";
      const typeCode = selectEquipType ? selectEquipType.value : "all";
      const q = inputEquipSearch ? inputEquipSearch.value : "";

      let url = "/api/catalog/equipment?limit=100";
      if (farmId) url += `&farm_id=${farmId}`;
      if (typeCode && typeCode !== "all") url += `&type_code=${typeCode}`;
      if (q && q.trim()) url += `&q=${encodeURIComponent(q.trim())}`;

      const res = await fetch(url);
      if (!res.ok) return;
      const equips = await res.json();

      if (!selectEquipment) return;
      selectEquipment.innerHTML = "";
      if (equips.length === 0) {
        selectEquipment.innerHTML = '<option value="">Nenhum equipamento encontrado</option>';
        return;
      }

      equips.forEach(e => {
        const opt = document.createElement("option");
        opt.value = e.equip_id;
        const radTxt = e.radius ? `${e.radius.toFixed(0)}m` : "-";
        const pressTxt = e.nominal_pressure ? `${e.nominal_pressure.toFixed(1)}bar` : "-";
        opt.textContent = `[${e.type_name}] ${e.equip_name} - ${e.maker} ${e.model} (R: ${radTxt}, P: ${pressTxt})`;
        if (e.equip_id === currentActiveEquipId) {
          opt.selected = true;
        }
        selectEquipment.appendChild(opt);
      });

      if (!selectEquipment.value && equips.length > 0) {
        selectEquipment.value = equips[0].equip_id;
      }
    } catch (err) {
      console.error("Erro ao carregar equipamentos:", err);
    }
  }

  async function applyEquipmentSwitch(equipId) {
    if (!equipId) return;
    const targetId = parseInt(equipId);
    try {
      const res = await fetch("/api/control/select-equipment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ equip_id: targetId })
      });
      if (res.ok) {
        const data = await res.json();
        currentActiveEquipId = targetId;
        addMcpLog(`[SCADA ATIVO ALTERADO] Equipamento #${targetId} selecionado com sucesso.`);
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: "select_equipment", equip_id: targetId }));
        }
      }
    } catch (err) {
      console.error("Erro ao alternar equipamento:", err);
    }
  }

  if (inputFarmSearch) {
    inputFarmSearch.addEventListener("input", debounce(async () => {
      await fetchFarms(inputFarmSearch.value);
      await fetchEquipment();
    }, 250));
  }

  if (selectFarm) {
    selectFarm.addEventListener("change", async () => {
      currentSelectedFarmId = parseInt(selectFarm.value);
      await fetchEquipment();
    });
  }

  if (selectEquipType) {
    selectEquipType.addEventListener("change", async () => {
      await fetchEquipment();
    });
  }

  if (inputEquipSearch) {
    inputEquipSearch.addEventListener("input", debounce(async () => {
      await fetchEquipment();
    }, 250));
  }

  if (btnApplyEquipment) {
    btnApplyEquipment.addEventListener("click", () => {
      if (selectEquipment && selectEquipment.value) {
        applyEquipmentSwitch(selectEquipment.value);
      }
    });
  }

  if (selectEquipment) {
    selectEquipment.addEventListener("change", () => {
      if (selectEquipment.value) {
        applyEquipmentSwitch(selectEquipment.value);
      }
    });
  }

  // Initial boots
  initHighcharts();
  connectWebSocket();
  fetchFarms().then(() => fetchEquipment());
});
