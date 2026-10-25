document.addEventListener("DOMContentLoaded", function () {
        const performanceGauge =
        document.querySelector(
            '[data-heart-rate-gauge]'
        );

    if (performanceGauge) {

        const progress =
            performanceGauge.querySelector(
                ".gauge-progress"
            );

        const valueElement =
            performanceGauge.querySelector(
                ".gauge-value"
            );

        if (progress && valueElement) {

            const currentBpm =
                Number(
                    valueElement.textContent.trim()
                );

            const minBpm = 60;
            const maxBpm = 140;

            let percentage =
                ((currentBpm - minBpm) /
                (maxBpm - minBpm)) * 100;

            percentage =
                Math.max(
                    0,
                    Math.min(100, percentage)
                );

            progress.setAttribute(
                "stroke-dasharray",
                `${percentage} ${100 - percentage}`
            );
        }
    }
    
    const heartGauge = document.querySelector("[data-heart-rate-gauge]");

    if (heartGauge) {
        const progress = heartGauge.querySelector(".gauge-progress");
        const valueElement = heartGauge.querySelector(".gauge-value");

        const currentBpm = Number(valueElement.textContent.trim());

        const minBpm = 60;
        const maxBpm = 140;

        // Calcula a porcentagem do BPM dentro da escala
        let percentage =
            ((currentBpm - minBpm) / (maxBpm - minBpm)) * 100;

        // Impede que o arco passe dos limites
        percentage = Math.max(0, Math.min(100, percentage));

        // Atualiza o arco
        progress.setAttribute(
            "stroke-dasharray",
            `${percentage} ${100 - percentage}`
        );
    }
    
    // =========================
    // EXIBIR / OCULTAR SENHA
    // =========================

    const eyeButtons = document.querySelectorAll(".eye");

    eyeButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            // Encontra o input de senha dentro do mesmo field
            const field = button.closest(".field");
            const passwordInput = field.querySelector("input");

            if (!passwordInput) {
                return;
            }

            // Alterna entre senha e texto
            if (passwordInput.type === "password") {

                passwordInput.type = "text";

                // Troca o ícone
                const icon = button.querySelector("i");

                if (icon) {
                    icon.classList.remove("ri-eye-fill");
                    icon.classList.add("ri-eye-off-fill");
                }

            } else {

                passwordInput.type = "password";

                // Volta o ícone
                const icon = button.querySelector("i");

                if (icon) {
                    icon.classList.remove("ri-eye-off-fill");
                    icon.classList.add("ri-eye-fill");
                }

            }

        });

    });
    
    // =========================
    // NAVEGAÇÃO DATA-NEXT
    // =========================

    const nextButtons = document.querySelectorAll("[data-next]");

    nextButtons.forEach(function (button) {

        // Não interfere no botão de motivo
        if (button.id === "reasonNextButton") {
            return;
        }

        button.addEventListener("click", function () {

            const nextPage = button.dataset.next;

            if (nextPage) {
                window.location.href = nextPage;
            }

        });

    });
    
    // =========================
    // ONBOARDING - MOTIVO
    // =========================

    const reasonButtons = document.querySelectorAll(
        '.choice-btn[data-choice]:not(#treatmentForm .choice-btn[data-choice])'
    );
    const reasonNextButton = document.getElementById("reasonNextButton");
    const reasonMessage = document.getElementById("choiceMessage");

    reasonButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            reasonButtons.forEach(function (otherButton) {
                otherButton.classList.remove("selected");
            });
            button.classList.add("selected");
            if (reasonMessage) reasonMessage.classList.remove("show");
        });
    });

    if (reasonNextButton) {
        reasonNextButton.addEventListener("click", async function () {
            const selectedButton = document.querySelector(
                '.choice-btn[data-choice].selected'
            );
            if (!selectedButton) {
                if (reasonMessage) reasonMessage.classList.add("show");
                return;
            }

            const endpoint = reasonNextButton.dataset.submit;
            if (!endpoint) {
                window.location.href = reasonNextButton.dataset.next;
                return;
            }

            reasonNextButton.disabled = true;
            try {
                const response = await fetch(endpoint, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: new URLSearchParams({ reason: selectedButton.dataset.choice })
                });
                const payload = await response.json();
                if (!response.ok) throw new Error(payload.error || "Não foi possível salvar sua resposta.");
                window.location.href = payload.next || reasonNextButton.dataset.next;
            } catch (error) {
                if (reasonMessage) {
                    reasonMessage.textContent = error.message || "Falha ao salvar a resposta. Tente novamente.";
                    reasonMessage.classList.add("show");
                }
            } finally {
                reasonNextButton.disabled = false;
            }
        });
    }

    // =========================
    // ACOMPANHAMENTO
    // =========================

    const treatmentForm =
        document.getElementById("treatmentForm");

    if (treatmentForm) {

        const treatmentButtons =
            treatmentForm.querySelectorAll(
                ".choice-btn[data-choice]"
            );

        const treatmentInput =
            document.getElementById("treatmentInput");

        const message =
            document.getElementById("choiceMessage");

        // =========================
        // CLICAR NAS OPÇÕES
        // =========================

        treatmentButtons.forEach(function (button) {

            button.addEventListener("click", function (event) {

                event.preventDefault();

                const choice =
                    button.dataset.choice;

                // -------------------------
                // NENHUM
                // -------------------------

                if (choice === "nenhum") {

                    // Remove seleção de todas
                    treatmentButtons.forEach(function (otherButton) {

                        otherButton.classList.remove("selected");

                    });

                    // Seleciona "Nenhum"
                    button.classList.add("selected");

                }

                // -------------------------
                // OUTRAS OPÇÕES
                // -------------------------

                else {

                    // Se clicar em qualquer acompanhamento,
                    // "Nenhum" é desmarcado.

                    const nenhumButton =
                        treatmentForm.querySelector(
                            '[data-choice="nenhum"]'
                        );

                    if (nenhumButton) {

                        nenhumButton.classList.remove(
                            "selected"
                        );

                    }

                    // IMPORTANTE:
                    // NÃO remove as outras opções.

                    // Isso permite:

                    // ☑ Psicoterapia
                    // ☑ Consulta médica
                    // ☑ Medicação

                    button.classList.toggle("selected");

                }


                // Esconde mensagem de erro

                if (message) {

                    message.classList.remove("show");

                }

            });

        });

        // =========================
        // CLICAR EM "PRÓXIMO"
        // =========================

        treatmentForm.addEventListener(
            "submit",
            function (event) {

                const selectedButtons =
                    treatmentForm.querySelectorAll(
                        ".choice-btn.selected"
                    );


                // -------------------------
                // NENHUMA SELEÇÃO
                // -------------------------

                if (selectedButtons.length === 0) {

                    event.preventDefault();

                    if (message) {

                        message.classList.add("show");

                    }

                    return;

                }

                // -------------------------
                // REMOVE INPUTS ANTIGOS
                // -------------------------

                treatmentForm
                    .querySelectorAll(
                        'input[name="treatment"]'
                    )
                    .forEach(function (input) {

                        input.remove();

                    });

                // -------------------------
                // CRIA UM INPUT PARA
                // CADA OPÇÃO SELECIONADA
                // -------------------------

                selectedButtons.forEach(
                    function (button) {

                        const input =
                            document.createElement("input");

                        input.type = "hidden";

                        input.name = "treatment";

                        input.value =
                            button.dataset.choice;

                        treatmentForm.appendChild(input);

                    }
                );


                // O formulário continua normalmente.
                // O navegador envia todos os inputs.
            }
        );

    }

    // =========================
    // MENU LATERAL
    // =========================

    const menuButtons = document.querySelectorAll("[data-menu]");
    const navDrawer = document.querySelector(".nav-drawer");

    menuButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            if (navDrawer) {
                navDrawer.classList.toggle("open");
            }

        });

    });

    // =========================
    // BOTÕES DO MENU
    // =========================

    const drawerButtons = document.querySelectorAll("[data-drawer-go]");

    drawerButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            const page = button.getAttribute("data-drawer-go");

            if (page) {
                window.location.href = page;
            }

        });

    });

    // =========================
    // FECHAR MENU AO CLICAR FORA
    // =========================

    if (navDrawer) {

        navDrawer.addEventListener("click", function (event) {

            if (event.target === navDrawer) {
                navDrawer.classList.remove("open");
            }

        });

    }

    // =========================
    // GRÁFICO DE ANSIEDADE
    // =========================

    const anxietyChart = document.querySelector("[data-anxiety-chart]");

    if (anxietyChart) {

        const anxietyData = [
            { day: "S", value: 7 },
            { day: "T", value: 3 },
            { day: "Q", value: 3 },
            { day: "Q", value: 0 },
            { day: "S", value: 0 },
            { day: "S", value: 3 },
            { day: "D", value: 7 }
        ];

        anxietyChart.innerHTML = `

            <div class="anxiety-chart-wrapper">

                <div class="anxiety-chart-scale">
                    <span>10</span>
                    <span>8</span>
                    <span>6</span>
                    <span>4</span>
                    <span>2</span>
                    <span>0</span>
                </div>

                <div class="anxiety-chart-content">

                    <div class="anxiety-chart-plot">

                        <div class="anxiety-chart-grid-lines">
                            <span></span>
                            <span></span>
                            <span></span>
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>

                        <div class="anxiety-chart-bars">

                            ${anxietyData.map(function (item) {

                                const barHeight = item.value === 0
                                    ? "0%"
                                    : `${item.value * 10}%`;

                                return `
                                    <div class="anxiety-chart-column">

                                        <div
                                            class="anxiety-chart-bar"
                                            style="height: ${barHeight};"
                                            title="${item.value} de 10"
                                        ></div>

                                    </div>
                                `;

                            }).join("")}

                        </div>

                    </div>

                    <div class="anxiety-chart-days">

                        ${anxietyData.map(function (item) {

                            return `
                                <span>${item.day}</span>
                            `;

                        }).join("")}

                    </div>

                </div>

            </div>

        `;

    }

    // =========================
    // BPM AO VIVO: dados persistidos no SQLite por usuário
    // =========================

    const heartRateGauges = document.querySelectorAll("[data-heart-rate-gauge]");
    const liveBpmLabels = document.querySelectorAll("[data-live-bpm]");

    function updateHeartRateFromServer(data) {
        const currentBpm = Number(data.bpm);
        const minBpm = Number(data.min_bpm);
        const maxBpm = Number(data.max_bpm);
        if (!Number.isFinite(currentBpm)) return;

        liveBpmLabels.forEach(function (element) {
            element.textContent = String(Math.round(currentBpm));
        });

        heartRateGauges.forEach(function (container) {
            const progress = container.querySelector(".gauge-progress");
            const value = container.querySelector(".gauge-value");
            const minimum = container.querySelector(".gauge-minmax");
            const maximum = container.querySelector(".gauge-max");
            const wave = container.querySelector(".gauge-wave");

            if (value) value.textContent = String(Math.round(currentBpm));
            if (minimum && Number.isFinite(minBpm)) minimum.textContent = String(Math.round(minBpm));
            if (maximum && Number.isFinite(maxBpm)) maximum.textContent = String(Math.round(maxBpm));

            const percentage = Math.max(0, Math.min(1, (currentBpm - 40) / 140));
            const filledArc = Math.max(0.1, 75 * percentage);
            if (progress) progress.setAttribute("stroke-dasharray", `${filledArc} ${100 - filledArc}`);
            if (wave) {
                const amplitude = 8 + percentage * 10;
                wave.setAttribute("d", `M35 112 H65 L87 ${112 - amplitude} L112 ${112 + amplitude} L134 ${112 - amplitude / 2} L154 112 H185`);
            }
        });
    }

    async function refreshLiveHeartRate() {
        try {
            const response = await fetch("/api/heart-rate/live", { credentials: "same-origin", cache: "no-store" });
            if (!response.ok) return;
            const data = await response.json();
            updateHeartRateFromServer(data);
        } catch (error) {
            console.warn("Não foi possível atualizar o BPM simulado.", error);
        }
    }

    if (heartRateGauges.length > 0 || liveBpmLabels.length > 0) {
        refreshLiveHeartRate();
        window.setInterval(refreshLiveHeartRate, 3000);
    }

    // =========================
    // GRÁFICO DE PRESSÃO ARTERIAL - DADOS REAIS DO BANCO
    // =========================
    const pressureChart = document.querySelector("[data-pressure-chart]");
    const pressureLabels = document.querySelector("[data-chart-labels]");
    const pressureButtons = document.querySelectorAll(".pressure-history .history-btn");
    const pressureHistoryNode = document.querySelector("[data-pressure-history]");

    if (pressureChart && pressureLabels && pressureButtons.length > 0 && pressureHistoryNode) {
        let pressureHistory = [];
        try {
            pressureHistory = JSON.parse(pressureHistoryNode.dataset.pressureHistory || "[]");
        } catch (error) {
            console.warn("Não foi possível interpretar o histórico de pressão.", error);
        }

        function localDay(date) {
            const d = new Date(date);
            return new Date(d.getFullYear(), d.getMonth(), d.getDate());
        }

        function summarize(period) {
            const now = new Date();
            const points = pressureHistory
                .map(item => ({ ...item, stamp: new Date(item.date) }))
                .filter(item => Number.isFinite(item.stamp.getTime()) && Number(item.sistolica) > 0);
            let buckets = [];

            if (period === "24h") {
                const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                buckets = Array.from({ length: 6 }, (_, i) => ({
                    label: `${String((now.getHours() - 20 + i * 4 + 24) % 24).padStart(2, "0")}h`,
                    start: new Date(start.getTime() + i * 4 * 60 * 60 * 1000),
                    end: new Date(start.getTime() + (i + 1) * 4 * 60 * 60 * 1000)
                }));
            } else if (period === "7d") {
                for (let i = 6; i >= 0; i--) {
                    const day = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
                    const end = new Date(day.getTime() + 24 * 60 * 60 * 1000);
                    buckets.push({ label: day.toLocaleDateString("pt-BR", { weekday: "short" }).replace(".", ""), start: day, end });
                }
            } else if (period === "30d") {
                for (let i = 5; i >= 0; i--) {
                    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i * 5 + 1);
                    const start = new Date(end.getFullYear(), end.getMonth(), end.getDate() - 5);
                    buckets.push({ label: `${String(start.getDate()).padStart(2, "0")}/${String(start.getMonth() + 1).padStart(2, "0")}`, start, end });
                }
            } else {
                for (let i = 2; i >= 0; i--) {
                    const start = new Date(now.getFullYear(), now.getMonth() - i, 1);
                    const end = new Date(now.getFullYear(), now.getMonth() - i + 1, 1);
                    buckets.push({ label: start.toLocaleDateString("pt-BR", { month: "short" }).replace(".", ""), start, end });
                }
            }

            return buckets.map(bucket => {
                const selected = points.filter(item => item.stamp >= bucket.start && item.stamp < bucket.end);
                const average = selected.length ? selected.reduce((sum, item) => sum + Number(item.sistolica), 0) / selected.length : null;
                // Altura visual baseada na sistólica, sem tratar a barra como diagnóstico.
                const value = average === null ? 0 : Math.max(8, Math.min(100, ((average - 80) / 90) * 100));
                return { label: bucket.label, value, average, count: selected.length };
            });
        }

        function updatePressureChart(period) {
            const rows = summarize(period);
            pressureChart.innerHTML = "";
            pressureLabels.innerHTML = "";
            pressureChart.style.gridTemplateColumns = `repeat(${rows.length}, minmax(0, 1fr))`;
            pressureLabels.style.gridTemplateColumns = `repeat(${rows.length}, minmax(0, 1fr))`;

            rows.forEach(row => {
                const column = document.createElement("div");
                column.className = "pressure-bar";
                column.style.height = `${row.value}%`;
                column.title = row.average === null
                    ? `${row.label}: sem medição`
                    : `${row.label}: média ${Math.round(row.average)} mmHg (${row.count} medição/ões)`;
                if (row.average === null) column.classList.add("empty");
                pressureChart.appendChild(column);

                const label = document.createElement("span");
                label.textContent = row.label;
                pressureLabels.appendChild(label);
            });

            pressureButtons.forEach(button => {
                button.classList.toggle("active", button.dataset.period === period);
            });
        }

        pressureButtons.forEach(button => button.addEventListener("click", () => updatePressureChart(button.dataset.period)));
        updatePressureChart("7d");
    }

    const weekButton = document.getElementById("weekButton");
    const weekMenu = document.getElementById("weekMenu");
    const weekArrow = document.getElementById("weekArrow");

    if (weekButton && weekMenu) {
        weekButton.addEventListener("click", function () {
            weekMenu.classList.toggle("active");

            if (weekMenu.classList.contains("active")) {
                weekArrow.textContent = "▲";
            } else {
                weekArrow.textContent = "▼";
            }
        });

        const weekOptions = weekMenu.querySelectorAll("button");

        weekOptions.forEach(function (option) {
            option.addEventListener("click", function () {
                const selectedWeek = option.getAttribute("data-week");

                document.querySelector(".week-date").textContent = selectedWeek;

                weekMenu.classList.remove("active");
                weekArrow.textContent = "▼";
            });
        });

        document.addEventListener("click", function (event) {
            if (!event.target.closest(".week-selector")) {
                weekMenu.classList.remove("active");
                weekArrow.textContent = "▼";
            }
        });
    }

});