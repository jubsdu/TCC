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

const reasonNextButton =
    document.getElementById("reasonNextButton");

const reasonMessage =

    document.getElementById("choiceMessage");

reasonButtons.forEach(function (button) {

    button.addEventListener("click", function () {

        // Remove seleção anterior
        reasonButtons.forEach(function (otherButton) {
            otherButton.classList.remove("selected");
        });

        // Seleciona o botão clicado
        button.classList.add("selected");

        // Esconde mensagem
        if (reasonMessage) {
            reasonMessage.classList.remove("show");
        }

    });

});

if (reasonNextButton) {

    reasonNextButton.addEventListener("click", function () {

        const selectedButton =
            document.querySelector(
                '.choice-btn[data-choice].selected'
            );

        // Não selecionou nada
        if (!selectedButton) {

            if (reasonMessage) {
                reasonMessage.classList.add("show");
            }

            return;
        }

        // Vai para a próxima página
        const nextPage =
            reasonNextButton.dataset.next;

        if (nextPage) {
            window.location.href = nextPage;
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
    
    // Atualizar gráfico de pressão

    function updatePressureChart(period) {

        const selectedData = pressureHistoryData[period];

        if (!selectedData) {
            return;
        }

        pressureChart.innerHTML = "";
        pressureLabels.innerHTML = "";

        const columnCount = selectedData.labels.length;

        pressureChart.style.gridTemplateColumns =
            `repeat(${columnCount}, 1fr)`;

        pressureLabels.style.gridTemplateColumns =
            `repeat(${columnCount}, 1fr)`;

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