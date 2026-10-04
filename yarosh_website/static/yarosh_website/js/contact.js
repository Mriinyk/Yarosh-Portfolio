const contactRadios = document.querySelectorAll('input[name="contact_method"]');
const usernameLabel = document.getElementById("dynamic_username_label");

if (usernameLabel instanceof HTMLLabelElement) {
    const updateUsernameLabel = (method) => {
        usernameLabel.textContent = method === "instagram"
            ? "Введіть Instagram нік"
            : "Введіть Telegram нік";
    };

    contactRadios.forEach((radio) => {
        radio.addEventListener("change", () => updateUsernameLabel(radio.value));
    });

    const selectedRadio = document.querySelector('input[name="contact_method"]:checked');
    if (selectedRadio instanceof HTMLInputElement) {
        updateUsernameLabel(selectedRadio.value);
    }
}
