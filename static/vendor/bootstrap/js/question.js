document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('medical-form');
    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            alert('Data sent successfully! It will be reviewed by the specialist.');
        });
    }
});