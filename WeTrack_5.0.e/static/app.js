/* =========================================================
   WeTrack 3.0 - Theme, charts and small UI interactions
   ========================================================= */
function setTheme(theme) {
    const valid = ["dark", "green", "light"];
    if (!valid.includes(theme)) theme = "default";
    if (document.body.classList.contains("auth-fixed")) return;
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("wetrack-theme", theme);
    document.querySelectorAll("[data-theme-choice]").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.themeChoice === theme);
    });
    refreshChartsForTheme();
}

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "default";
    setTheme(current === "dark" ? "green" : current === "green" ? "light" : "dark");
}

(function initTheme() {
    if (document.body.classList.contains("auth-fixed")) return;
    const saved = localStorage.getItem("wetrack-theme") || "dark";
    setTheme(saved);
    setTimeout(() => document.querySelectorAll(".toast").forEach(x => {
        x.style.opacity = "0";
        x.style.transform = "translateX(30px)";
        x.style.transition = ".5s";
        setTimeout(() => x.remove(), 500);
    }), 3500);
})();

function chartDefaults() {
    const theme = document.documentElement.getAttribute("data-theme") || "default";
    const dark = theme === "dark";
    const green = theme === "green";
    const text = dark ? "#91a7c0" : green ? "#607568" : "#68798a";
    const grid = dark ? "rgba(145,184,222,.06)" : green ? "rgba(80,120,95,.10)" : "rgba(80,105,130,.10)";
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: text, font: { size: 10 } } } },
        scales: {
            x: { ticks: { color: text, font: { size: 9 } }, grid: { color: grid } },
            y: { ticks: { color: text, font: { size: 9 } }, grid: { color: grid } }
        }
    };
}

function refreshChartsForTheme() {
    if (typeof Chart === "undefined" || typeof Chart.getChart !== "function") return;
    const theme = document.documentElement.getAttribute("data-theme") || "dark";
    const accent = theme === "green" ? "#3d9b63" : theme === "light" ? "#d83a4d" : "#35c2ff";
    const text = theme === "dark" ? "#91a7c0" : theme === "green" ? "#607568" : "#68798a";
    const grid = theme === "dark" ? "rgba(145,184,222,.10)" : theme === "green" ? "rgba(80,120,95,.15)" : "rgba(80,105,130,.15)";
    const palettes = {
        dark: ["#35c2ff", "#8063ff", "#35c991", "#f2b156", "#e36b80", "#9bb0c7"],
        green: ["#3d9b63", "#91c78b", "#d5ae57", "#63a4aa", "#82b6a2", "#607568"],
        light: ["#d83a4d", "#2d8fc4", "#38a879", "#e5a43a", "#a86bd1", "#8b98a5"]
    };
    document.querySelectorAll("canvas").forEach(canvas => {
        const chart = Chart.getChart(canvas);
        if (!chart) return;
        const legendLabels = chart.options.plugins?.legend?.labels;
        if (legendLabels) legendLabels.color = text;
        Object.values(chart.options.scales || {}).forEach(scale => {
            scale.ticks = { ...(scale.ticks || {}), color: text };
            if (scale.grid) scale.grid.color = grid;
        });
        chart.data.datasets.forEach(dataset => {
            if (["progressChart", "predictionActivityChart"].includes(canvas.id)) {
                dataset.borderColor = accent;
                dataset.backgroundColor = `${accent}22`;
                dataset.pointBackgroundColor = accent;
            } else if (["activityChart", "sleepChart", "predictionSleepChart"].includes(canvas.id)) {
                dataset.backgroundColor = `${accent}99`;
                dataset.borderColor = accent;
            } else if (["dashboardDietChart", "nutritionChart", "predictionDietChart"].includes(canvas.id)) {
                dataset.backgroundColor = palettes[theme];
            }
        });
        chart.update("none");
    });
}
function lastNDates(days) {
    const result = [];
    const now = new Date();
    now.setHours(12, 0, 0, 0);
    for (let i = days - 1; i >= 0; i--) {
        const d = new Date(now);
        d.setDate(now.getDate() - i);
        result.push(d.toISOString().slice(0, 10));
    }
    return result;
}

function renderDashboardCharts(act, progress, sleep) {
    const labels7 = lastNDates(7), labels14 = lastNDates(14);
    const ad = {}, pd = {}, sd = {};
    act.forEach(x => ad[String(x.activityDate).slice(0, 10)] = Number(x.calories || 0));
    progress.forEach(x => pd[String(x.activityDate).slice(0, 10)] = Number(x.totalMinutes || 0));
    sleep.forEach(x => sd[String(x.sleepDate).slice(0, 10)] = Number(x.durationHours));
    const display = labels => labels.map(d => { const [y,m,day] = d.split('-').map(Number); return new Date(y,m-1,day).toLocaleDateString(undefined,{month:'short',day:'numeric'}); });
    const color = getComputedStyle(document.documentElement).getPropertyValue('--chart-accent').trim() || '#35c2ff';
    const common = chartDefaults();
    const kcal = document.getElementById('activityChart');
    if (kcal) new Chart(kcal,{type:'bar',data:{labels:display(labels7),datasets:[{label:'kcal',data:labels7.map(d=>ad[d]||0),backgroundColor:color+'99',borderColor:color,borderWidth:1,borderRadius:6,maxBarThickness:30}]},options:{...common,plugins:{...common.plugins,legend:{display:false}},scales:{...common.scales,y:{...common.scales.y,beginAtZero:true,title:{display:true,text:'kcal'}}}}});
    const mins = document.getElementById('progressChart');
    if (mins) new Chart(mins,{type:'line',data:{labels:display(labels14),datasets:[{label:'Minutes',data:labels14.map(d=>pd[d]||0),tension:.36,fill:true,borderColor:color,backgroundColor:color+'20',pointRadius:3,pointHoverRadius:5,pointBackgroundColor:color}]},options:{...common,plugins:{...common.plugins,legend:{display:false}},scales:{...common.scales,y:{...common.scales.y,beginAtZero:true,title:{display:true,text:'minutes'}}}}});
    const c3=document.getElementById('sleepChart');
    if(c3) new Chart(c3,{type:'bar',data:{labels:display(labels14),datasets:[{label:'Hours',data:labels14.map(d=>sd[d]??null),borderRadius:5,backgroundColor:color+'99'}]},options:common});
}
function renderDietChart(groups, targetId = "nutritionChart", chartType = "doughnut") {
    const c = document.getElementById(targetId);
    if (!c) return;
    const theme = document.documentElement.getAttribute("data-theme") || "default";
    const text = theme === "dark" ? "#91a7c0" : theme === "green" ? "#607568" : "#68798a";
    new Chart(c, {
        type: chartType,
        data: { labels: groups.map(x => x.foodGroup), datasets: [{ data: groups.map(x => Number(x.calories)), backgroundColor: ["#d83a4d", "#2d8fc4", "#38a879", "#e5a43a", "#a86bd1", "#8b98a5"], borderWidth: 0 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom", labels: { color: text, font: { size: 10 }, padding: 12 } }, tooltip: { callbacks: { label: context => { const total = context.dataset.data.reduce((sum, value) => sum + Number(value || 0), 0); const percent = total ? Math.round(Number(context.raw) / total * 100) : 0; return `${context.label}: ${percent}%`; } } } } }
    });
}

function renderPredictionCharts(activity, sleep, diet) {
    const a = document.getElementById("predictionActivityChart");
    if (a) new Chart(a, { type: "line", data: { labels: activity.map(x => x.activityDate), datasets: [{ label: "Minutes", data: activity.map(x => Number(x.totalMinutes)), tension: .35, borderColor: "#d83a4d", backgroundColor: "rgba(216,58,77,.10)", fill: true, pointRadius: 3 }] }, options: chartDefaults() });
    const s = document.getElementById("predictionSleepChart");
    if (s) new Chart(s, { type: "bar", data: { labels: sleep.map(x => x.sleepDate), datasets: [{ label: "Hours", data: sleep.map(x => Number(x.durationHours)), backgroundColor: "rgba(45,143,196,.55)", borderRadius: 5 }] }, options: chartDefaults() });
    renderDietChart(diet, "predictionDietChart", "pie");
}

function setupDietPreview() {
    const select = document.getElementById("foodID");
    const qty = document.getElementById("quantity");
    const out = document.getElementById("calPreview");
    const search = document.getElementById("foodSearch");
    if (!select || !qty || !out) return;

    function update() {
        const o = select.options[select.selectedIndex];
        const calories = Number(o?.dataset.cal || 0) * Number(qty.value || 0);
        out.textContent = calories.toFixed(0) + " kcal";
    }

    select.addEventListener("change", update);
    qty.addEventListener("input", update);
    update();

    // Keep the existing food search, but do not submit anything here.
    // The selected food is only added to the temporary meal builder when
    // the user presses "+ Add to Meal".
    if (search) search.addEventListener("input", () => {
        const q = search.value.toLowerCase().trim();
        [...select.options].forEach(o => {
            o.hidden = !o.textContent.toLowerCase().includes(q);
        });
        if (select.selectedOptions[0]?.hidden) {
            const first = [...select.options].find(o => !o.hidden);
            if (first) {
                select.value = first.value;
                update();
            }
        }
    });
}

function initDialogs() {
    document.querySelectorAll('[data-open-dialog], [data-info-target]').forEach(button => button.addEventListener('click', () => {
        const dialogId = button.dataset.openDialog || button.dataset.infoTarget;
        document.getElementById(dialogId)?.showModal();
    }));
    document.querySelectorAll('dialog').forEach(dialog => {
        dialog.querySelectorAll('.modal-close,.modal-cancel,.modal-ok').forEach(button => button.addEventListener('click', () => dialog.close()));
        dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
    });
}
function initRegistrationDraft() {
    const storageKey = 'wetrack.registrationDraft';
    const form = document.querySelector('.auth-card form.form-grid');
    if (!form) {
        const successToast = [...document.querySelectorAll('.toast.success')].some(toast => toast.textContent.includes('Account created'));
        if (successToast) sessionStorage.removeItem(storageKey);
        return;
    }
    const fields = [...form.elements].filter(field => field.name && field.type !== 'password' && field.type !== 'submit');
    try {
        const saved = JSON.parse(sessionStorage.getItem(storageKey) || '{}');
        fields.forEach(field => {
            if (!(field.name in saved)) return;
            if (field.type === 'checkbox') field.checked = saved[field.name] === field.value;
            else field.value = saved[field.name];
        });
        const persist = () => {
            const draft = {};
            fields.forEach(field => { draft[field.name] = field.type === 'checkbox' ? (field.checked ? field.value : '') : field.value; });
            sessionStorage.setItem(storageKey, JSON.stringify(draft));
        };
        form.addEventListener('input', persist);
        form.addEventListener('change', persist);
        persist();
    } catch (error) {
        // Registration remains usable when browser storage is unavailable.
    }
}
document.addEventListener('DOMContentLoaded', initDialogs);
document.addEventListener('DOMContentLoaded', initRegistrationDraft);

