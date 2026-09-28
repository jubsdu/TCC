function openLogoutPopup() {
    const popup = document.getElementById("logoutPopup");

    if (popup) {
        popup.classList.add("active");
    }
}

function closeLogoutPopup() {
    const popup = document.getElementById("logoutPopup");

    if (popup) {
        popup.classList.remove("active");
    }
}

function logout() {
    // Fecha o popup
    closeLogoutPopup();

    // Redireciona para a tela de login
    window.location.href = "/login";
}

// Fecha ao clicar no fundo escuro
document.addEventListener("click", function (event) {
    const popup = document.getElementById("logoutPopup");

    if (
        popup &&
        event.target === popup
    ) {
        closeLogoutPopup();
    }
});

// Fecha ao apertar ESC
document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
        closeLogoutPopup();
    }
});