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
  let isSwitchingAsset = false;

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

    // 0. Update Header & Active Asset Badges (only if not currently switching assets)
    if (!isSwitchingAsset && ((!currentActiveSpec && tel.id_equip) || (currentActiveSpec && currentActiveSpec.equip_id !== tel.id_equip))) {
      fetch(`/api/catalog/equipment/${tel.id_equip}`)
        .then(r => r.json())
        .then(sp => {
          if (isSwitchingAsset) return;
          currentActiveSpec = sp;
          if (sp.farm_id) currentSelectedFarmId = sp.farm_id;
          syncActiveAssetUI(currentActiveSpec, tel);
        })
        .catch(() => {});
    }

    if (!isSwitchingAsset) {
      if (headerFarmName && tel.farm_name) {
        const loc = tel.farm_city ? ` - ${tel.farm_city}${tel.farm_state ? ', ' + tel.farm_state : ''}` : '';
        headerFarmName.textContent = `Fazenda ${tel.farm_name}${loc}`;
      }
      if (headerPivotName && tel.pivot_name) {
        const maker = tel.pivot_maker || (currentActiveSpec ? currentActiveSpec.maker : "Valmont");
        const model = tel.pivot_model || (currentActiveSpec ? currentActiveSpec.model : "");
        headerPivotName.textContent = `${tel.pivot_name} (${maker} ${model})`.trim();
      }
      if (badgeActiveEquip && tel.pivot_name) {
        badgeActiveEquip.textContent = `${tel.pivot_name} (#${tel.id_equip})`;
      }
      if (badgeActiveMaker) {
        const maker = tel.pivot_maker || (currentActiveSpec ? currentActiveSpec.maker : "Valmont");
        const model = tel.pivot_model || (currentActiveSpec ? currentActiveSpec.model : "");
        badgeActiveMaker.textContent = `${maker} ${model}`.trim();
      }
      if (badgeActiveRadius && tel.pivot_radius) {
        badgeActiveRadius.textContent = `${tel.pivot_radius.toFixed(0)} m`;
      }
      if (badgeActivePressure && tel.nominal_pressure) {
        badgeActivePressure.textContent = `${tel.nominal_pressure.toFixed(2)} bar`;
      }
    }

    if (copilotSpecLiveP && tel.pressure_begin !== undefined) {
      copilotSpecLiveP.textContent = `${tel.pressure_begin.toFixed(2)} bar`;
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

  let currentSelectedFarmId = 1515; // default
  let currentActiveEquipId = 14863;  // default
  let currentActiveSpec = null;

  function syncActiveAssetUI(spec, tel = null) {
    if (!spec) return;

    // 0. Synchronize Dropdown Selectors (Aba 1) so they NEVER diverge
    if (selectFarm && spec.farm_id) {
      currentSelectedFarmId = parseInt(spec.farm_id);
      let opt = Array.from(selectFarm.options).find(o => o.value === String(spec.farm_id));
      if (!opt) {
        opt = document.createElement("option");
        opt.value = spec.farm_id;
        const loc = spec.farm_city ? `${spec.farm_city}${spec.farm_state ? ", " + spec.farm_state : ""}` : "";
        opt.textContent = `${spec.farm_name}${loc ? " - " + loc : ""}`;
        selectFarm.prepend(opt);
      }
      selectFarm.value = String(spec.farm_id);
    }

    if (selectEquipment && spec.equip_id) {
      currentActiveEquipId = parseInt(spec.equip_id);
      let opt = Array.from(selectEquipment.options).find(o => o.value === String(spec.equip_id));
      if (!opt) {
        opt = document.createElement("option");
        opt.value = spec.equip_id;
        const type = spec.type_name || "Pivô Central";
        opt.textContent = `[${type}] ${spec.equip_name} - ${spec.maker || ""} ${spec.model || ""}`.trim();
        selectEquipment.prepend(opt);
      }
      selectEquipment.value = String(spec.equip_id);
    }

    // 1. Sync SCADA Header & Active Asset Badges (Aba 1)
    if (headerFarmName) {
      const loc = spec.farm_city ? ` - ${spec.farm_city}${spec.farm_state ? ', ' + spec.farm_state : ''}` : '';
      headerFarmName.textContent = `Fazenda ${spec.farm_name}${loc}`;
    }
    if (headerPivotName) {
      headerPivotName.textContent = `${spec.equip_name} (${spec.maker} ${spec.model})`.trim();
    }
    if (badgeActiveEquip) {
      badgeActiveEquip.textContent = `${spec.equip_name} (#${spec.equip_id})`;
    }
    if (badgeActiveMaker) {
      badgeActiveMaker.textContent = `${spec.maker} ${spec.model}`.trim();
    }
    if (badgeActiveRadius) {
      const rad = spec.radius ? `${spec.radius.toFixed(0)} m` : '-';
      badgeActiveRadius.textContent = rad;
    }
    if (badgeActivePressure) {
      const nomP = spec.nominal_pressure ? `${spec.nominal_pressure.toFixed(2)} bar` : '-';
      badgeActivePressure.textContent = nomP;
    }

    // 2. Sync Copilot RAG Relational Specification Cards (Aba 2)
    if (copilotSpecName) {
      copilotSpecName.textContent = `${spec.equip_name} (#${spec.equip_id})`;
    }
    if (copilotSpecMaker) {
      copilotSpecMaker.textContent = `${spec.maker} ${spec.model}`.trim();
    }
    if (copilotSpecFarm) {
      const loc = spec.farm_city ? ` (${spec.farm_city}${spec.farm_state ? ', ' + spec.farm_state : ''})` : '';
      copilotSpecFarm.textContent = `${spec.farm_name}${loc}`;
    }
    if (copilotSpecNomP) {
      copilotSpecNomP.textContent = `${(spec.nominal_pressure || 3.4).toFixed(2)} bar`;
    }
    if (copilotSpecFlow) {
      copilotSpecFlow.textContent = `${(spec.flow_rate || 185.0).toFixed(1)} m³/h`;
    }
    if (copilotSpecRadius) {
      const ha = spec.area ? ` (${spec.area.toFixed(1)} ha)` : '';
      copilotSpecRadius.textContent = `${(spec.radius || 380.0).toFixed(0)} m${ha}`;
    }
    if (copilotSpecDepth) {
      const flow = spec.flow_rate || 185.0;
      const areaHa = spec.area || 45.0;
      const nomDepth = (flow * 18.0) / (areaHa * 10.0);
      copilotSpecDepth.textContent = `${nomDepth.toFixed(1)} mm (Nominal)`;
    }

    // 3. Live field pressure in Copilot (clean format, no duplicate bar unit)
    if (copilotSpecLiveP) {
      let liveP = null;
      if (tel && tel.pressure_begin !== undefined) {
        liveP = tel.pressure_begin;
      } else if (kpiPressure && kpiPressure.textContent) {
        liveP = parseFloat(kpiPressure.textContent);
      }
      if (liveP !== null && !isNaN(liveP)) {
        copilotSpecLiveP.textContent = `${liveP.toFixed(2)} bar`;
      }
    }
  }

  function debounce(func, wait = 300) {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  async function fetchFarms(searchQuery = "", ensureFarmId = null) {
    try {
      const targetFarmId = ensureFarmId || currentSelectedFarmId;
      let url = `/api/catalog/farms?q=${encodeURIComponent(searchQuery)}&limit=300`;
      if (targetFarmId) {
        url += `&include_farm_id=${targetFarmId}`;
      }
      const res = await fetch(url);
      if (!res.ok) return;
      const farms = await res.json();

      if (!selectFarm) return;
      selectFarm.innerHTML = "";
      if (farms.length === 0) {
        selectFarm.innerHTML = '<option value="">Nenhuma fazenda encontrada</option>';
        return;
      }

      // Check if targetFarmId is in farms. If not, and we have currentActiveSpec, prepend it.
      if (targetFarmId && !farms.some(f => f.farm_id === targetFarmId) && currentActiveSpec && currentActiveSpec.farm_id === targetFarmId) {
        farms.unshift({
          farm_id: currentActiveSpec.farm_id,
          farm_name: currentActiveSpec.farm_name,
          farm_city: currentActiveSpec.farm_city,
          farm_state: currentActiveSpec.farm_state,
          total_equips: 1,
        });
      }

      farms.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f.farm_id;
        const location = f.farm_city ? `${f.farm_city}${f.farm_state ? ", " + f.farm_state : ""}` : "";
        const locTxt = location ? ` - ${location}` : "";
        opt.textContent = `${f.farm_name} (${f.total_equips} equips)${locTxt}`;
        if (f.farm_id === targetFarmId) {
          opt.selected = true;
        }
        selectFarm.appendChild(opt);
      });

      if (targetFarmId && farms.some(f => f.farm_id === targetFarmId)) {
        selectFarm.value = String(targetFarmId);
      } else if (!selectFarm.value && farms.length > 0) {
        selectFarm.value = farms[0].farm_id;
      }
      currentSelectedFarmId = parseInt(selectFarm.value);
    } catch (err) {
      console.error("Erro ao carregar fazendas:", err);
    }
  }

  async function fetchEquipment(ensureEquipId = null, farmChanged = false) {
    try {
      const farmId = selectFarm ? selectFarm.value : (currentSelectedFarmId || "");
      const typeCode = selectEquipType ? selectEquipType.value : "all";
      const q = inputEquipSearch ? inputEquipSearch.value : "";

      // If the user changed the farm, do NOT carry over targetEquipId from another farm!
      let targetEquipId = ensureEquipId;
      if (!farmChanged && !targetEquipId) {
        if (currentActiveSpec && String(currentActiveSpec.farm_id) === String(farmId)) {
          targetEquipId = currentActiveEquipId;
        }
      }

      let url = "/api/catalog/equipment?limit=200";
      if (farmId) url += `&farm_id=${farmId}`;
      if (typeCode && typeCode !== "all") url += `&type_code=${typeCode}`;
      if (q && q.trim()) url += `&q=${encodeURIComponent(q.trim())}`;
      if (targetEquipId) url += `&include_equip_id=${targetEquipId}`;

      const res = await fetch(url);
      if (!res.ok) return;
      let equips = await res.json();

      // If no equipment found for this specific type on the selected farm, fallback to "all"
      if (equips.length === 0 && typeCode !== "all") {
        if (selectEquipType) selectEquipType.value = "all";
        let fallbackUrl = "/api/catalog/equipment?limit=200";
        if (farmId) fallbackUrl += `&farm_id=${farmId}`;
        if (q && q.trim()) fallbackUrl += `&q=${encodeURIComponent(q.trim())}`;
        if (targetEquipId) fallbackUrl += `&include_equip_id=${targetEquipId}`;
        const fallbackRes = await fetch(fallbackUrl);
        if (fallbackRes.ok) {
          equips = await fallbackRes.json();
        }
      }

      if (!selectEquipment) return;
      selectEquipment.innerHTML = "";
      if (equips.length === 0) {
        selectEquipment.innerHTML = '<option value="">Nenhum equipamento encontrado</option>';
        return;
      }

      // If targetEquipId is not in equips, but currentActiveSpec matches AND belongs to this farm, prepend it
      if (
        targetEquipId &&
        !equips.some(e => e.equip_id === targetEquipId) &&
        currentActiveSpec &&
        currentActiveSpec.equip_id === targetEquipId &&
        String(currentActiveSpec.farm_id) === String(farmId)
      ) {
        equips.unshift(currentActiveSpec);
      }

      equips.forEach(e => {
        const opt = document.createElement("option");
        opt.value = e.equip_id;
        const radTxt = e.radius ? `${e.radius.toFixed(0)}m` : "-";
        const pressTxt = e.nominal_pressure ? `${e.nominal_pressure.toFixed(1)}bar` : "-";
        opt.textContent = `[${e.type_name || 'Pivô'}] ${e.equip_name} - ${e.maker || ''} ${e.model || ''} (R: ${radTxt}, P: ${pressTxt})`.trim();
        if (targetEquipId && e.equip_id === targetEquipId) {
          opt.selected = true;
        }
        selectEquipment.appendChild(opt);
      });

      if (targetEquipId && equips.some(e => e.equip_id === targetEquipId)) {
        selectEquipment.value = String(targetEquipId);
      } else if (equips.length > 0) {
        selectEquipment.value = String(equips[0].equip_id);
      }
    } catch (err) {
      console.error("Erro ao carregar equipamentos:", err);
    }
  }

  async function applyEquipmentSwitch(equipId) {
    if (!equipId) return;
    const targetId = parseInt(equipId);
    isSwitchingAsset = true;
    try {
      const res = await fetch("/api/control/select-equipment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ equip_id: targetId })
      });
      if (res.ok) {
        const data = await res.json();
        currentActiveEquipId = targetId;
        if (data.catalog_spec) {
          currentActiveSpec = data.catalog_spec;
        } else {
          const specRes = await fetch(`/api/catalog/equipment/${targetId}`);
          if (specRes.ok) currentActiveSpec = await specRes.json();
        }
        if (currentActiveSpec && currentActiveSpec.farm_id) {
          currentSelectedFarmId = currentActiveSpec.farm_id;
        }
        syncActiveAssetUI(currentActiveSpec);
        addMcpLog(`[SCADA ATIVO ALTERADO] #${targetId} ${currentActiveSpec ? currentActiveSpec.equip_name : ''} ativado.`);
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: "select_equipment", equip_id: targetId }));
        }
      }
    } catch (err) {
      console.error("Erro ao alternar equipamento:", err);
    } finally {
      setTimeout(() => {
        isSwitchingAsset = false;
      }, 400);
    }
  }

  if (inputFarmSearch) {
    inputFarmSearch.addEventListener("input", debounce(async () => {
      await fetchFarms(inputFarmSearch.value, currentSelectedFarmId);
      await fetchEquipment(currentActiveEquipId);
    }, 250));
  }

  if (selectFarm) {
    selectFarm.addEventListener("change", async () => {
      const newFarmId = parseInt(selectFarm.value);
      if (!newFarmId) return;
      currentSelectedFarmId = newFarmId;
      isSwitchingAsset = true;

      // Lock selectors temporarily to prevent race conditions during asset transition
      selectFarm.disabled = true;
      if (selectEquipment) selectEquipment.disabled = true;

      try {
        // 1. Fetch equipment belonging to this new farm without carrying over old equip ID
        await fetchEquipment(null, true);

        // 2. Automatically activate the first equipment of this newly selected farm
        if (selectEquipment && selectEquipment.value) {
          await applyEquipmentSwitch(selectEquipment.value);
        }
      } catch (err) {
        console.error("Erro ao alternar fazenda:", err);
      } finally {
        selectFarm.disabled = false;
        if (selectEquipment) selectEquipment.disabled = false;
      }
    });
  }

  if (selectEquipType) {
    selectEquipType.addEventListener("change", async () => {
      await fetchEquipment();
      if (selectEquipment && selectEquipment.value) {
        await applyEquipmentSwitch(selectEquipment.value);
      }
    });
  }

  if (inputEquipSearch) {
    inputEquipSearch.addEventListener("input", debounce(async () => {
      await fetchEquipment(currentActiveEquipId);
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

  // ---------------------------------------------------------------------------
  // 2-TAB NAVIGATION (SCADA vs COPILOTO)
  // ---------------------------------------------------------------------------
  const tabBtnScada = document.getElementById("tab-btn-scada");
  const tabBtnCopilot = document.getElementById("tab-btn-copilot");
  const tabContentScada = document.getElementById("tab-content-scada");
  const tabContentCopilot = document.getElementById("tab-content-copilot");

  function switchTab(target) {
    if (target === "scada") {
      if (tabContentScada) tabContentScada.classList.remove("hidden");
      if (tabContentCopilot) tabContentCopilot.classList.add("hidden");
      if (tabBtnScada) {
        tabBtnScada.className = "flex items-center space-x-2.5 px-5 py-3 border-b-2 border-emerald-400 font-bold text-xs text-white bg-slate-800/70 rounded-t-xl transition shadow-sm -mb-px";
        tabBtnScada.innerHTML = `
          <i data-lucide="gauge" class="w-4 h-4 text-emerald-400"></i>
          <span>Aba 1: Supervisório SCADA Polar</span>
          <span class="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            ATIVA
          </span>
        `;
      }
      if (tabBtnCopilot) {
        tabBtnCopilot.className = "flex items-center space-x-2.5 px-5 py-3 border-b-2 border-transparent font-medium text-xs text-slate-400 hover:text-slate-200 hover:border-slate-700 hover:bg-slate-800/30 rounded-t-xl transition -mb-px";
        tabBtnCopilot.innerHTML = `
          <i data-lucide="bot" class="w-4 h-4 text-slate-400"></i>
          <span>Aba 2: Copiloto Cognitivo (LangGraph)</span>
          <span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800/80 text-slate-400 border border-slate-700/60">
            System 2
          </span>
        `;
      }
      if (window.lucide) window.lucide.createIcons();
      setTimeout(() => {
        if (polarChart) polarChart.reflow();
        if (timeSeriesChart) timeSeriesChart.reflow();
      }, 50);
    } else {
      if (tabContentScada) tabContentScada.classList.add("hidden");
      if (tabContentCopilot) tabContentCopilot.classList.remove("hidden");
      if (tabBtnCopilot) {
        tabBtnCopilot.className = "flex items-center space-x-2.5 px-5 py-3 border-b-2 border-cyan-400 font-bold text-xs text-white bg-slate-800/70 rounded-t-xl transition shadow-sm -mb-px";
        tabBtnCopilot.innerHTML = `
          <i data-lucide="bot" class="w-4 h-4 text-cyan-400"></i>
          <span>Aba 2: Copiloto Cognitivo (LangGraph)</span>
          <span class="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
            <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
            ATIVA
          </span>
        `;
      }
      if (tabBtnScada) {
        tabBtnScada.className = "flex items-center space-x-2.5 px-5 py-3 border-b-2 border-transparent font-medium text-xs text-slate-400 hover:text-slate-200 hover:border-slate-700 hover:bg-slate-800/30 rounded-t-xl transition -mb-px";
        tabBtnScada.innerHTML = `
          <i data-lucide="gauge" class="w-4 h-4 text-slate-400"></i>
          <span>Aba 1: Supervisório SCADA Polar</span>
          <span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800/80 text-slate-400 border border-slate-700/60">
            Aba 1
          </span>
        `;
      }
      if (window.lucide) window.lucide.createIcons();
      updateCopilotCards();
    }
  }

  if (tabBtnScada) tabBtnScada.addEventListener("click", () => switchTab("scada"));
  if (tabBtnCopilot) tabBtnCopilot.addEventListener("click", () => switchTab("copilot"));

  // ---------------------------------------------------------------------------
  // COPILOTO COGNITIVO (LANGGRAPH + RELATIONAL RAG)
  // ---------------------------------------------------------------------------
  let copilotSessionId = "session_" + Math.random().toString(36).substring(2, 9);
  let pendingCopilotHitlAction = null;

  const copilotChatForm = document.getElementById("copilot-chat-form");
  const copilotChatInput = document.getElementById("copilot-chat-input");
  const copilotMessagesContainer = document.getElementById("copilot-messages-container");
  const copilotHitlBanner = document.getElementById("copilot-hitl-banner");
  const copilotHitlReason = document.getElementById("copilot-hitl-reason");
  const btnCopilotApproveHitl = document.getElementById("btn-copilot-approve-hitl");
  const btnCopilotSyncTelemetry = document.getElementById("btn-copilot-sync-telemetry");
  const btnCopilotClearChat = document.getElementById("btn-copilot-clear-chat");

  const copilotSpecName = document.getElementById("copilot-spec-name");
  const copilotSpecMaker = document.getElementById("copilot-spec-maker");
  const copilotSpecFarm = document.getElementById("copilot-spec-farm");
  const copilotSpecNomP = document.getElementById("copilot-spec-nom-p");
  const copilotSpecLiveP = document.getElementById("copilot-spec-live-p");
  const copilotSpecFlow = document.getElementById("copilot-spec-flow");
  const copilotSpecRadius = document.getElementById("copilot-spec-radius");
  const copilotSpecDepth = document.getElementById("copilot-spec-depth");
  const finopsTierBadge = document.getElementById("finops-tier-badge");
  const finopsLatency = document.getElementById("finops-latency");

  function appendCopilotMessage(sender, htmlContent, isUser = false) {
    if (!copilotMessagesContainer) return;
    const msgDiv = document.createElement("div");
    msgDiv.className = isUser ? "flex items-start justify-end space-x-3" : "flex items-start space-x-3";

    if (isUser) {
      msgDiv.innerHTML = `
        <div class="bg-slate-800 text-slate-100 border border-slate-700/80 rounded-2xl px-4 py-2.5 max-w-xl shadow-md">
          <p class="font-medium text-xs">${htmlContent}</p>
        </div>
        <div class="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 flex-shrink-0 mt-0.5">
          <i data-lucide="user" class="w-4 h-4"></i>
        </div>
      `;
    } else {
      msgDiv.innerHTML = `
        <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 flex-shrink-0 mt-0.5">
          <i data-lucide="bot" class="w-4 h-4"></i>
        </div>
        <div class="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 text-slate-300 max-w-2xl space-y-2 shadow-md leading-relaxed">
          ${htmlContent}
        </div>
      `;
    }

    copilotMessagesContainer.appendChild(msgDiv);
    copilotMessagesContainer.scrollTop = copilotMessagesContainer.scrollHeight;
    if (window.lucide) window.lucide.createIcons();
  }

  function appendTypingIndicator() {
    const typingId = "typing-" + Date.now();
    const div = document.createElement("div");
    div.id = typingId;
    div.className = "flex items-start space-x-3";
    div.innerHTML = `
      <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 flex-shrink-0 mt-0.5">
        <i data-lucide="cpu" class="w-4 h-4 animate-spin"></i>
      </div>
      <div class="bg-slate-950/80 border border-slate-800 rounded-2xl px-4 py-3 text-slate-400 max-w-xs flex items-center space-x-2">
        <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
        <span class="text-xs">Consultando DuckDB & Executando StateGraph...</span>
      </div>
    `;
    copilotMessagesContainer.appendChild(div);
    copilotMessagesContainer.scrollTop = copilotMessagesContainer.scrollHeight;
    if (window.lucide) window.lucide.createIcons();
    return typingId;
  }

  async function sendCopilotQuery(queryText) {
    if (!queryText || !queryText.trim()) return;
    const cleanQuery = queryText.trim();
    if (copilotChatInput) copilotChatInput.value = "";

    appendCopilotMessage("Operador", cleanQuery, true);
    const typingId = appendTypingIndicator();

    try {
      const res = await fetch("/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: cleanQuery,
          equip_id: currentActiveEquipId || 14863,
          session_id: copilotSessionId,
        })
      });

      const typingEl = document.getElementById(typingId);
      if (typingEl) typingEl.remove();

      if (res.ok) {
        const data = await res.json();
        const mdText = data.response_markdown || "Sem resposta.";
        const renderedHtml = window.marked ? window.marked.parse(mdText) : `<pre class="whitespace-pre-wrap">${mdText}</pre>`;
        appendCopilotMessage("Copiloto", renderedHtml, false);

        if (data.catalog_spec) {
          currentActiveSpec = data.catalog_spec;
          syncActiveAssetUI(currentActiveSpec, data.telemetry_live);
        }

        if (data.deficit_metrics && copilotSpecDepth) {
          copilotSpecDepth.textContent = `${data.deficit_metrics.actual_depth_mm} mm (Nominal: ${data.deficit_metrics.nominal_depth_mm} mm)`;
        }

        if (data.finops) {
          if (finopsTierBadge) finopsTierBadge.textContent = data.finops.tier_used || "System 1 Hybrid Fallback";
          if (finopsLatency) finopsLatency.textContent = `${data.finops.latency_ms || 12} ms`;
        }

        if (data.requires_hitl && data.hitl_action) {
          pendingCopilotHitlAction = data.hitl_action;
          if (copilotHitlBanner) copilotHitlBanner.classList.remove("hidden");
          if (copilotHitlReason) copilotHitlReason.textContent = data.hitl_action.reason || "Queda severa de pressão detectada.";
          addMcpLog(`[COPILOT HITL ALERTA] Ação de segurança pendente para #${data.equip_id}`);
        } else {
          if (copilotHitlBanner) copilotHitlBanner.classList.add("hidden");
          pendingCopilotHitlAction = null;
        }

      } else {
        appendCopilotMessage("Sistema", `<span class="text-red-400 font-bold">Erro HTTP ${res.status} ao consultar o copiloto.</span>`, false);
      }
    } catch (err) {
      console.error("Erro na consulta do copiloto:", err);
      const typingEl = document.getElementById(typingId);
      if (typingEl) typingEl.remove();
      appendCopilotMessage("Sistema", `<span class="text-red-400 font-bold">Falha de conexão: ${err.message}</span>`, false);
    }
  }

  async function updateCopilotCards() {
    if (!currentActiveSpec) {
      try {
        const res = await fetch(`/api/catalog/equipment/${currentActiveEquipId || 14863}`);
        if (res.ok) {
          currentActiveSpec = await res.json();
        }
      } catch (e) {
        console.warn("Falha ao buscar especificação ativa:", e);
      }
    }
    syncActiveAssetUI(currentActiveSpec);
  }

  if (copilotChatForm) {
    copilotChatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (copilotChatInput) sendCopilotQuery(copilotChatInput.value);
    });
  }

  document.querySelectorAll(".copilot-shortcut").forEach((btn) => {
    btn.addEventListener("click", () => {
      const q = btn.getAttribute("data-query");
      if (q) sendCopilotQuery(q);
    });
  });

  if (btnCopilotApproveHitl) {
    btnCopilotApproveHitl.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/copilot/hitl/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ticket_id: "HITL-COPILOT-" + Date.now(),
            operator_name: "Operador_Henrique",
          })
        });
        if (res.ok) {
          appendCopilotMessage("Sistema", `
            <div class="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-300">
              <strong class="font-bold flex items-center gap-1.5"><i data-lucide="shield-check" class="w-4 h-4 text-emerald-400"></i> Ordem de Parada Emergencial Aprovada!</strong>
              <p class="text-xs mt-1 text-slate-300">O comando de desarme e despressurização foi transmitido via FastMCP tool ao CLP com registro de auditoria.</p>
            </div>
          `, false);
          if (copilotHitlBanner) copilotHitlBanner.classList.add("hidden");
          addMcpLog("[HITL APROVADO VIA COPILOTO] Desarme do CLP executado pelo operador.");
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: "approve_hitl", ticket_id: "TICKET-AUTO" }));
          }
        }
      } catch (err) {
        console.error("Erro ao aprovar HITL do copiloto:", err);
      }
    });
  }

  if (btnCopilotSyncTelemetry) {
    btnCopilotSyncTelemetry.addEventListener("click", () => {
      updateCopilotCards();
      addMcpLog("[COPILOTO] Ficha técnica e telemetria sincronizadas.");
    });
  }

  if (btnCopilotClearChat) {
    btnCopilotClearChat.addEventListener("click", () => {
      if (copilotMessagesContainer) {
        copilotMessagesContainer.innerHTML = `
          <div class="flex items-start space-x-3">
            <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 flex-shrink-0 mt-0.5">
              <i data-lucide="bot" class="w-4 h-4"></i>
            </div>
            <div class="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 text-slate-300 max-w-2xl space-y-2">
              <p class="font-bold text-white">Histórico reiniciado. Como posso auxiliar na operação industrial?</p>
              <p class="text-slate-400">Pronto para novas análises em tempo real ou consultas via RAG Relacional.</p>
            </div>
          </div>
        `;
        if (window.lucide) window.lucide.createIcons();
      }
    });
  }

  // Initial boots
  initHighcharts();
  connectWebSocket();

  // Initialize active asset from backend status first, then populate selectors
  fetch("/api/status")
    .then(r => r.json())
    .then(status => {
      if (status && status.current_telemetry && status.current_telemetry.id_equip) {
        currentActiveEquipId = status.current_telemetry.id_equip;
        if (status.current_telemetry.id_farm) {
          currentSelectedFarmId = status.current_telemetry.id_farm;
        }
      }
      return fetch(`/api/catalog/equipment/${currentActiveEquipId}`);
    })
    .then(r => r.json())
    .then(spec => {
      if (spec) {
        currentActiveSpec = spec;
        if (spec.farm_id) currentSelectedFarmId = spec.farm_id;
        syncActiveAssetUI(currentActiveSpec);
      }
    })
    .catch(err => console.warn("Erro ao obter ativo inicial:", err))
    .finally(async () => {
      await fetchFarms("", currentSelectedFarmId);
      await fetchEquipment(currentActiveEquipId);
      if (currentActiveSpec) {
        syncActiveAssetUI(currentActiveSpec);
      }
    });
});
