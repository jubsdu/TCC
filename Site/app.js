
document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // BOTÕES "PRÓXIMO"
    // =========================

    const nextButtons = document.querySelectorAll("[data-next]");

    nextButtons.forEach(function (button) {

        button.addEventListener("click", function (event) {

            const choiceButtons = document.querySelectorAll("[data-choice]");
            const selectedChoice = document.querySelector("[data-choice].selected");
            const message = document.querySelector("#choiceMessage");

            if (choiceButtons.length > 0 && !selectedChoice) {

                event.preventDefault();

                if (message) {
                    message.classList.add("show");
                }

                return;
            }

            const nextPage = button.getAttribute("data-next");

            if (nextPage) {
                window.location.href = nextPage;
            }

        });

    });


    // =========================
    // SELEÇÃO DAS OPÇÕES
    // =========================

    const choiceButtons = document.querySelectorAll("[data-choice]");

    choiceButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            choiceButtons.forEach(function (otherButton) {
                otherButton.classList.remove("selected");
            });

            button.classList.add("selected");

            const message = document.querySelector("#choiceMessage");

            if (message) {
                message.classList.remove("show");
            }

        });

    });


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
    // MEDIDOR DE FREQUÊNCIA CARDÍACA
    // =========================

    const heartRateGauges =
        document.querySelectorAll("[data-heart-rate-gauge]");

    if (heartRateGauges.length > 0) {

        const STORAGE_KEY = "vitapulse-heart-rate";

        let currentBpm = 82;
        let minBpm = 62;
        let maxBpm = 124;


        // Recuperar dados salvos

        try {

            const savedData =
                JSON.parse(localStorage.getItem(STORAGE_KEY));

            if (savedData) {

                currentBpm = Number(savedData.currentBpm) || 82;
                minBpm = Number(savedData.minBpm) || 62;
                maxBpm = Number(savedData.maxBpm) || 124;

            }

        } catch (error) {

            console.log(
                "Não foi possível recuperar os dados do medidor."
            );

        }


        // Limitar valores

        function clamp(value, min, max) {

            return Math.max(
                min,
                Math.min(max, value)
            );

        }


        // Atualizar medidor

        function updateHeartRate(bpm) {

            currentBpm = Math.round(
                clamp(bpm, 40, 180)
            );

            minBpm = Math.min(
                minBpm,
                currentBpm
            );

            maxBpm = Math.max(
                maxBpm,
                currentBpm
            );


            const percentage = clamp(
                (currentBpm - 40) / 140,
                0,
                1
            );

            const arcPercentage = 75;

            const filledArc = Math.max(
                0.1,
                arcPercentage * percentage
            );


            heartRateGauges.forEach(function (container) {

                const gaugeProgress =
                    container.querySelector(".gauge-progress");

                const gaugeValue =
                    container.querySelector(".gauge-value");

                const gaugeMinMax =
                    container.querySelectorAll(".gauge-minmax");

                const gaugeWave =
                    container.querySelector(".gauge-wave");


                if (
                    !gaugeProgress ||
                    !gaugeValue ||
                    gaugeMinMax.length < 2 ||
                    !gaugeWave
                ) {

                    console.warn(
                        "Elementos do medidor não encontrados.",
                        container
                    );

                    return;

                }


                // Valor principal

                gaugeValue.textContent = currentBpm;


                // Valores mínimo e máximo

                gaugeMinMax[0].textContent = minBpm;
                gaugeMinMax[1].textContent = maxBpm;


                // Arco do medidor

                gaugeProgress.setAttribute(
                    "stroke-dasharray",
                    `${filledArc} ${100 - filledArc}`
                );


                // Onda do coração

                const amplitude = 8 + percentage * 10;

                const wavePath = `
                    M35 112
                    H65
                    L87 ${112 - amplitude}
                    L112 ${112 + amplitude}
                    L134 ${112 - amplitude / 2}
                    L154 112
                    H185
                `;

                gaugeWave.setAttribute(
                    "d",
                    wavePath
                );

            });


            // Salvar dados

            try {

                localStorage.setItem(
                    STORAGE_KEY,
                    JSON.stringify({
                        currentBpm: currentBpm,
                        minBpm: minBpm,
                        maxBpm: maxBpm
                    })
                );

            } catch (error) {

                console.log(
                    "Não foi possível salvar os dados do medidor."
                );

            }

        }


        // Disponibilizar função globalmente

        window.updateHeartRate = updateHeartRate;


        // Iniciar medidor

        updateHeartRate(currentBpm);


        // Simulação automática

        setInterval(function () {

            const variation =
                Math.floor(Math.random() * 11) - 5;

            const nextBpm = clamp(
                currentBpm + variation,
                60,
                140
            );

            updateHeartRate(nextBpm);

        }, 2500);

    }


    // =========================
    // GRÁFICO DE PRESSÃO ARTERIAL
    // =========================

    const pressureChart =
        document.querySelector("[data-pressure-chart]");

    const pressureLabels =
        document.querySelector("[data-chart-labels]");

    const pressureButtons =
        document.querySelectorAll(
            ".pressure-history .history-btn"
        );


    if (
        pressureChart &&
        pressureLabels &&
        pressureButtons.length > 0
    ) {

        const pressureHistoryData = {

            "24h": {
                values: [35, 65, 48, 82, 58, 38],
                labels: [
                    "00h",
                    "04h",
                    "08h",
                    "12h",
                    "16h",
                    "20h"
                ]
            },

            "7d": {
                values: [55, 72, 45, 88, 62, 76, 52],
                labels: [
                    "Seg",
                    "Ter",
                    "Qua",
                    "Qui",
                    "Sex",
                    "Sáb",
                    "Dom"
                ]
            },

            "30d": {
                values: [42, 68, 55, 78, 48, 85, 62],
                labels: [
                    "01",
                    "05",
                    "10",
                    "15",
                    "20",
                    "25",
                    "30"
                ]
            },

            "3m": {
                values: [60, 45, 75, 52, 88, 65],
                labels: [
                    "Jul",
                    "Ago",
                    "Set",
                    "Out",
                    "Nov",
                    "Dez"
                ]
            }

        };


        // Atualizar gráfico de pressão

        function updatePressureChart(period) {

            const selectedData =
                pressureHistoryData[period];

            if (!selectedData) {
                return;
            }


            // Limpar gráfico anterior

            pressureChart.innerHTML = "";

            pressureLabels.innerHTML = "";


            // Criar colunas do gráfico

            selectedData.values.forEach(function (value) {

                const column =
                    document.createElement("div");

                column.className = "pressure-bar";

                column.style.height = value + "%";

                pressureChart.appendChild(column);

            });


            // Criar rótulos inferiores

            selectedData.labels.forEach(function (label) {

                const text =
                    document.createElement("span");

                text.textContent = label;

                pressureLabels.appendChild(text);

            });


            // Atualizar botão ativo

            pressureButtons.forEach(function (button) {

                const isActive =
                    button.dataset.period === period;

                button.classList.toggle(
                    "active",
                    isActive
                );

            });

        }


        // Eventos dos botões de pressão

        pressureButtons.forEach(function (button) {

            button.addEventListener("click", function () {

                const selectedPeriod =
                    button.dataset.period;

                updatePressureChart(selectedPeriod);

            });

        });


        // Iniciar gráfico em 24 horas

        updatePressureChart("24h");

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