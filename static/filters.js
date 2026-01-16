// Filter functions for HH Parser

function applyFilters() {
    const minSalary = document.getElementById('minSalary').value;
    const hideEmpty = document.getElementById('hideEmpty').checked;

    const filters = {};
    if (minSalary) filters.min_salary = parseInt(minSalary);
    filters.hide_empty = hideEmpty;

    // Reload data with filters
    loadData(filters);
}

function resetFilters() {
    document.getElementById('minSalary').value = '';
    document.getElementById('hideEmpty').checked = true;

    // Reload data without filters
    loadData({});
}

function showFilterNotification(originalCount, filteredCount) {
    const message = `Показано ${filteredCount} из ${originalCount} вакансий`;
    showStatus(message);
    setTimeout(hideStatus, 3000);
}

// Update loadVacancies to support filters
const originalLoadVacancies = loadVacancies;
async function loadVacancies(filters = {}) {
    try {
        // Build query params
        const params = new URLSearchParams();
        if (filters.min_salary) params.append('min_salary', filters.min_salary);
        if (filters.hide_empty !== undefined) params.append('hide_empty', filters.hide_empty);

        const queryString = params.toString();
        const url = `/api/vacancies${queryString ? '?' + queryString : ''}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.success && data.vacancies) {
            const tbody = document.getElementById('vacanciesBody');
            tbody.innerHTML = '';

            data.vacancies.forEach(vacancy => {
                const row = document.createElement('tr');

                const salary = vacancy.salary_from || vacancy.salary_to
                    ? `${vacancy.salary_from || '?'} - ${vacancy.salary_to || '?'} ${vacancy.salary_currency || '₽'}`
                    : 'Не указана';

                row.innerHTML = `
                    <td><a href="${vacancy.url}" target="_blank">${vacancy.name}</a></td>
                    <td>${vacancy.company_name || 'Не указана'}</td>
                    <td>${salary}</td>
                    <td>${vacancy.experience || 'Не указан'}</td>
                    <td><a href="${vacancy.url}" target="_blank" class="btn-link">🔗</a></td>
                `;

                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Error loading vacancies:', error);
    }
}
