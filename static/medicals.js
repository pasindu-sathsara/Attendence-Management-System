let medicalPage = 1, medicalRequest = 0;
function medicalKey(row) {
    return {course: row.course_code + '~' + row.academic_year,
        session: row.date + '|' + row.week_number, email: row.email};
}
function documentLink(row) {
    const link = document.createElement('a'); link.textContent = 'Download';
    link.href = '/api/medical-file?' + new URLSearchParams(medicalKey(row));
    return link;
}
function reviewButtons(row) {
    const actions = document.createElement('div'); actions.className = 'medical-actions';
    if (row.medical_status !== 'pending') { actions.textContent = '—'; return actions; }
    if (row.medical_kind === 'special' && document.body.dataset.role !== 'ar') {
        actions.textContent = 'AR review'; return actions;
    }
    for (const [title, decision] of [['Approve', 'approved'], ['Reject', 'rejected']]) {
        const button = document.createElement('button'); button.textContent = title; button.className = 'secondary';
        button.onclick = async () => {
            if (!confirm(title + ' ' + submissionType(row.medical_kind) + ' for ' + row.reg + '?')) return;
            for (const item of actions.querySelectorAll('button')) item.disabled = true;
            try {
                await api('/api/medical-review', {...medicalKey(row), decision});
                await loadMedicals(medicalPage); message('review-message', submissionType(row.medical_kind) + ' ' + decision + '.');
            } catch (error) {
                message('review-message', error.message, true);
                for (const item of actions.querySelectorAll('button')) item.disabled = false;
            }
        };
        actions.append(button);
    }
    return actions;
}
async function loadMedicals(page = 1) {
    const version = ++medicalRequest;
    try {
        const result = await api('/api/medical-submissions?' + new URLSearchParams({page, status: $('medical-filter').value}));
        if (version !== medicalRequest) return;
        medicalPage = result.page;
        tableRows($('medical-rows'), result.rows, [r => r.reg, r => r.name, r => moduleLabel(r.course_code),
            r => r.date + ' · Week ' + r.week_number, r => submissionType(r.medical_kind),
            r => r.medical_status, documentLink, reviewButtons]);
        pager('medical-pager', result, loadMedicals);
    } catch (error) { if (version === medicalRequest) message('review-message', error.message, true); }
}
$('medical-filter').onchange = () => loadMedicals();
loadMedicals();
