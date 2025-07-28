// Alter and Success Message
window.onload = function () {
    const errorBox = document.querySelector('.error-message');
    const successBox = document.querySelector('.success-message');
    const success = document.querySelector('.success');
    if (errorBox) {
        setTimeout(() => { errorBox.style.display = 'none'; }, 3000)
    }
    if (successBox) {
        setTimeout(() => { successBox.style.display = 'none'; }, 3000);
    }
    if (success) {
        setTimeout(() => { success.style.display = 'none'; }, 2000);
    }
}


