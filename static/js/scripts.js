// Custom scripts for the Inventory Control System

// Example: AJAX search functionality for the list_items page
document.addEventListener('DOMContentLoaded', function () {
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(searchForm);
            fetch(searchForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newTable = doc.querySelector('table');
                const oldTable = document.querySelector('table');
                if (newTable && oldTable) {
                    oldTable.parentNode.replaceChild(newTable, oldTable);
                }
            })
            .catch(error => console.error('Error:', error));
        });
    }
});
