// HH.ru Parser - Dashboard JavaScript

let keywordsChart, skillsChart, experienceChart;
let currentData = null; // Store data for filtering

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    loadData();
    setupEventListeners();

    // Auto-refresh every 5 seconds if collecting
    setInterval(checkStatus, 5000);
});

function setupEventListeners() {
    document.getElementById('collectBtn').addEventListener('click', openModal);
    document.getElementById('refreshBtn').addEventListener('click', loadData);
    document.getElementById('exportJsonBtn').addEventListener('click', () => exportData('json'));
    document.getElementById('exportCsvBtn').addEventListener('click', () => exportData('csv'));

    // Modal controls
    document.getElementById('closeModal').addEventListener('click', closeModal);
    document.getElementById('cancelBtn').addEventListener('click', closeModal);
    document.getElementById('startCollectBtn').addEventListener('click', startCollection);

    // Update estimated total when inputs change
    document.getElementById('searchPages').addEventListener('input', updateEstimatedTotal);
    document.getElementById('searchPerPage').addEventListener('change', updateEstimatedTotal);

    // Project controls
    document.getElementById('projectSelect').addEventListener('change', switchProject);
    document.getElementById('deleteProjectBtn').addEventListener('click', deleteProject);
    document.getElementById('createNewProject').addEventListener('change', function () {
        document.getElementById('projectName').style.display = this.checked ? 'block' : 'none';
    });

    // Filters
    const applyBtn = document.getElementById('applyFilters');
    const resetBtn = document.getElementById('resetFilters');
    if (applyBtn) applyBtn.addEventListener('click', applyFilters);
    if (resetBtn) resetBtn.addEventListener('click', resetFilters);

    // Close modal on outside click
    document.getElementById('settingsModal').addEventListener('click', (e) => {
        if (e.target.id === 'settingsModal') closeModal();
    });
}

async function loadData(filters = {}) {
    try {
        // Load projects first
        await loadProjects();

        // Build query params
        const params = new URLSearchParams();
        if (filters.min_salary) params.append('min_salary', filters.min_salary);
        if (filters.hide_empty !== undefined) params.append('hide_empty', filters.hide_empty);

        const queryString = params.toString();
        const url = `/api/stats${queryString ? '?' + queryString : ''}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.success && data.total_vacancies > 0) {
            currentData = data; // Store for filtering
            updateStats(data);
            updateCharts(data.report);
            await loadVacancies(filters);

            // Show filter notification (temporarily disabled to prevent loop)
            // if (data.filtered) {
            //     showFilterNotification(data.original_count, data.total_vacancies);  
            // }
        } else {
            console.log('No data yet - database is empty');
            currentData = null;
        }
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

function updateStats(data) {
    const report = data.report;

    document.getElementById('totalVacancies').textContent = data.total_vacancies;

    // Average salary
    if (report.salary_stats && report.salary_stats.avg_from) {
        const avgSalary = Math.round(report.salary_stats.avg_from);
        document.getElementById('avgSalary').textContent =
            new Intl.NumberFormat('ru-RU').format(avgSalary) + ' ₽';
    } else {
        document.getElementById('avgSalary').textContent = '-';
    }

    // Top skill
    if (report.top_skills && report.top_skills.length > 0) {
        document.getElementById('topSkills').textContent = report.top_skills[0][0];
    } else {
        document.getElementById('topSkills').textContent = '-';
    }

    // With salary percentage
    if (report.salary_stats && report.salary_stats.count_total > 0) {
        const percentage = Math.round(
            (report.salary_stats.count_with_salary / report.salary_stats.count_total) * 100
        );
        document.getElementById('withSalary').textContent = percentage + '%';
    } else {
        document.getElementById('withSalary').textContent = '0%';
    }
}

function updateCharts(report) {
    if (!report) return;

    // Keywords chart
    if (report.top_keywords && report.top_keywords.length > 0) {
        const keywordsData = report.top_keywords.slice(0, 20);
        keywordsChart.data.labels = keywordsData.map(k => k[0]);
        keywordsChart.data.datasets[0].data = keywordsData.map(k => k[1]);
        keywordsChart.update();
    }

    // Skills chart
    if (report.top_skills && report.top_skills.length > 0) {
        const skillsData = report.top_skills.slice(0, 15);
        skillsChart.data.labels = skillsData.map(s => s[0]);
        skillsChart.data.datasets[0].data = skillsData.map(s => s[1]);
        skillsChart.update();
    }

    // Experience chart
    if (report.experience_stats && Object.keys(report.experience_stats).length > 0) {
        const expData = Object.entries(report.experience_stats);
        experienceChart.data.labels = expData.map(e => e[0]);
        experienceChart.data.datasets[0].data = expData.map(e => e[1]);
        experienceChart.update();
    }
}

async function loadVacancies(filters = {}) {
    try {
        // Build query params
        const params = new URLSearchParams({ per_page: 10 });
        if (filters.min_salary) params.append('min_salary', filters.min_salary);
        if (filters.hide_empty !== undefined) params.append('hide_empty', filters.hide_empty);

        const queryString = params.toString();
        const url = `/api/vacancies?${queryString}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.success && data.vacancies.length > 0) {
            const tbody = document.getElementById('vacanciesBody');
            tbody.innerHTML = '';

            data.vacancies.forEach(vacancy => {
                const row = document.createElement('tr');

                const salaryText = formatSalary(vacancy);

                row.innerHTML = `
                    <td><strong>${escapeHtml(vacancy.name || 'N/A')}</strong></td>
                    <td>${escapeHtml(vacancy.company_name || 'N/A')}</td>
                    <td>${salaryText}</td>
                    <td>${escapeHtml(vacancy.experience || 'N/A')}</td>
                    <td><a href="${vacancy.url}" target="_blank" rel="noopener">Открыть</a></td>
                `;

                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Error loading vacancies:', error);
    }
}

function formatSalary(vacancy) {
    if (vacancy.salary_from || vacancy.salary_to) {
        const currency = vacancy.salary_currency === 'RUR' ? '₽' : vacancy.salary_currency;
        let salaryText = '';

        if (vacancy.salary_from && vacancy.salary_to) {
            salaryText = `${formatNumber(vacancy.salary_from)} - ${formatNumber(vacancy.salary_to)} ${currency}`;
        } else if (vacancy.salary_from) {
            salaryText = `от ${formatNumber(vacancy.salary_from)} ${currency}`;
        } else if (vacancy.salary_to) {
            salaryText = `до ${formatNumber(vacancy.salary_to)} ${currency}`;
        }

        return `<span class="salary-badge">${salaryText}</span>`;
    }
    return '<span style="color: #94a3b8;">Не указана</span>';
}

function formatNumber(num) {
    return new Intl.NumberFormat('ru-RU').format(num);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function startCollection() {
    const btn = document.getElementById('startCollectBtn');
    btn.disabled = true;
    closeModal();

    // Get parameters from form
    const createNew = document.getElementById('createNewProject').checked;
    const params = {
        query: document.getElementById('searchQuery').value,
        area: document.getElementById('searchArea').value || null,
        experience: document.getElementById('searchExperience').value || null,
        max_pages: parseInt(document.getElementById('searchPages').value),
        per_page: parseInt(document.getElementById('searchPerPage').value),
        create_new_project: createNew
    };

    if (createNew) {
        params.project_name = document.getElementById('projectName').value || params.query;
    }

    try {
        const response = await fetch('/api/collect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(params)
        });
        const data = await response.json();

        if (data.success) {
            showStatus('Сбор вакансий начат...');
        } else {
            alert('Ошибка: ' + data.error);
            btn.disabled = false;
        }
    } catch (error) {
        console.error('Error starting collection:', error);
        btn.disabled = false;
    }
}

async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const data = await response.json();

        if (data.success) {
            const select = document.getElementById('projectSelect');
            const currentBackendId = data.current_project_id;
            select.innerHTML = '';

            data.projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.id;
                option.textContent = `${project.name} (${project.vacancy_count || 0} вакансий)`;
                select.appendChild(option);
            });

            // Sync with backend's current project
            select.value = currentBackendId;
        }
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

async function switchProject() {
    const projectId = parseInt(document.getElementById('projectSelect').value);

    try {
        await fetch(`/api/projects/${projectId}/switch`, { method: 'POST' });
        loadData();
    } catch (error) {
        console.error('Error switching project:', error);
    }
}

async function deleteProject() {
    const projectId = parseInt(document.getElementById('projectSelect').value);

    if (projectId === 1) {
        alert('Нельзя удалить основной проект!');
        return;
    }

    if (!confirm('Удалить этот проект и все его вакансии?')) {
        return;
    }

    try {
        const response = await fetch(`/api/projects/${projectId}`, { method: 'DELETE' });
        const data = await response.json();

        if (data.success) {
            await loadData();
        } else {
            alert('Ошибка: ' + data.error);
        }
    } catch (error) {
        console.error('Error deleting project:', error);
    }
}

function openModal() {
    document.getElementById('settingsModal').classList.remove('hidden');
    updateEstimatedTotal();
}

function closeModal() {
    document.getElementById('settingsModal').classList.add('hidden');
}

function updateEstimatedTotal() {
    const pages = parseInt(document.getElementById('searchPages').value) || 1;
    const perPage = parseInt(document.getElementById('searchPerPage').value) || 20;
    const total = pages * perPage;
    document.getElementById('estimatedTotal').textContent = total;
}

// Global variable to store current filters
let currentFilters = {};

async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();

        if (status.running) {
            showStatus(status.message);
            document.getElementById('collectBtn').disabled = true;
        } else {
            if (document.getElementById('statusBar').classList.contains('hidden') === false) {
                // Collection just finished
                hideStatus();
                // Force reload projects to sync with backend
                await loadProjects();
                // Then load data for current project WITH current filters
                await loadData(currentFilters);
            }
            document.getElementById('collectBtn').disabled = false;
        }
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

function showStatus(message) {
    const statusBar = document.getElementById('statusBar');
    const statusMessage = document.getElementById('statusMessage');

    statusBar.classList.remove('hidden');
    statusMessage.textContent = message;
}

function hideStatus() {
    document.getElementById('statusBar').classList.add('hidden');
}

function exportData(format) {
    window.location.href = `/api/export/${format}`;
}

function initCharts() {
    const chartColors = {
        primary: 'rgb(99, 102, 241)',
        secondary: 'rgb(139, 92, 246)',
        success: 'rgb(16, 185, 129)',
        info: 'rgb(14, 165, 233)',
        warning: 'rgb(245, 158, 11)',
    };

    // Keywords chart
    const keywordsCtx = document.getElementById('keywordsChart').getContext('2d');
    keywordsChart = new Chart(keywordsCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Частота упоминаний',
                data: [],
                backgroundColor: createGradient(keywordsCtx, chartColors.primary),
                borderRadius: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });

    // Skills chart
    const skillsCtx = document.getElementById('skillsChart').getContext('2d');
    skillsChart = new Chart(skillsCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Количество вакансий',
                data: [],
                backgroundColor: createGradient(skillsCtx, chartColors.success),
                borderRadius: 8,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { beginAtZero: true }
            }
        }
    });

    // Experience chart
    const expCtx = document.getElementById('experienceChart').getContext('2d');
    experienceChart = new Chart(expCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    chartColors.primary,
                    chartColors.success,
                    chartColors.warning,
                    chartColors.info,
                ],
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        font: { size: 14 }
                    }
                }
            }
        }
    });
}

function createGradient(ctx, color) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, color);
    // Convert rgb(r,g,b) to rgba(r,g,b,0.5) for transparency
    const rgbaColor = color.replace('rgb', 'rgba').replace(')', ', 0.5)');
    gradient.addColorStop(1, rgbaColor);
    return gradient;
}

// Filter functions
function applyFilters() {
    const minSalary = document.getElementById('minSalary').value;
    const hideEmpty = document.getElementById('hideEmpty').checked;

    const filters = {};
    if (minSalary) filters.min_salary = parseInt(minSalary);
    filters.hide_empty = hideEmpty;

    currentFilters = filters; // Store globally to persist through checkStatus
    loadData(filters);
}

function resetFilters() {
    document.getElementById('minSalary').value = '';
    document.getElementById('hideEmpty').checked = true;

    currentFilters = {}; // Clear global filters
    loadData({});
}

function showFilterNotification(originalCount, filteredCount) {
    const message = `Показано ${filteredCount} из ${originalCount} вакансий`;
    showStatus(message);
    setTimeout(hideStatus, 3000);
}

