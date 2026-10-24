const reportStaff = ['hod', 'ar'].includes(document.body.dataset.role);
let reportOptions = {courses: [], semesters: [], batches: []};
let reportStudents = [], selectedStudents = new Set();
let reportVersion = 0, studentRequest = 0, reportResult = null, reportBusy = false;

function reportParams(course = '') {
    const params = new URLSearchParams({academic_year: $('report-year').value});
    if ($('report-semester').value) params.set('semester_number', $('report-semester').value);
    if (reportStaff && $('report-batch').value) params.set('batch', $('report-batch').value);
    if (course) params.set('course', course);
    return params.toString();
}
function selectedBody() {
    return {registrations: $('select-all').checked ? null : [...selectedStudents]};
}
function clearReport() {
    reportVersion++;
    $('report-results').hidden = true;
    $('register-preview').hidden = true;
    message('report-message', '');
}
function selectionCount() {
    $('selection-count').textContent = selectedStudents.size + ' students selected';
    const disabled = !selectedStudents.size || reportBusy;
    for (const id of ['view-report', 'download', 'download-students']) $(id).disabled = disabled;
}
function studentPage(page = 1) {
    const search = $('student-search').value.toLowerCase().trim();
    const rows = reportStudents.filter(r => (r.reg + ' ' + r.name).toLowerCase().includes(search));
    tableRows($('student-rows'), rows.slice((page - 1) * 10, page * 10), [r => {
        const box = document.createElement('input');
        box.type = 'checkbox'; box.checked = selectedStudents.has(r.reg);
        box.setAttribute('aria-label', 'Select ' + r.reg);
        box.onchange = () => {
            if (box.checked) selectedStudents.add(r.reg); else selectedStudents.delete(r.reg);
            $('select-all').checked = reportStudents.length > 0 && selectedStudents.size === reportStudents.length;
            clearReport(); selectionCount();
        };
        return box;
    }, r => r.reg, r => r.name]);
    pager('student-pager', {total: rows.length, page, pages: Math.max(1, Math.ceil(rows.length / 10))}, studentPage);
}
async function loadReportStudents() {
    clearReport();
    const version = ++studentRequest;
    reportStudents = []; selectedStudents.clear(); selectionCount(); studentPage();
    if (!$('report-year').value) return;
    try {
        const result = await api('/api/report-students?' + reportParams());
        if (version !== studentRequest) return;
        reportStudents = result.rows;
        selectedStudents = new Set(reportStudents.map(r => r.reg));
        $('select-all').checked = reportStudents.length > 0;
        selectionCount(); studentPage();
    } catch (error) {
        if (version === studentRequest) message('report-message', error.message, true);
    }
}
const studentColumns = [['Reg No', r => r.reg], ['Name', r => r.name], ['Present', r => r.present],
    ['Absent', r => r.absent], ['MC', r => r.medical], ['Special Medical', r => r.special],
    ['Excused', r => r.excused], ['Total Sessions', r => r.total], ['Attendance %', percentage],
    ['Eligibility', r => r.eligibility]];
function summaryPage(page = 1) {
    const columns = reportResult.kind === 'modules'
        ? [['Module', r => moduleLabel(r.course_code)], ['Students', r => r.students],
           ['Total Sessions', r => r.total], ['Average Attendance %', percentage]]
        : studentColumns;
    $('report-head').replaceChildren();
    for (const [title] of columns) {
        const th = document.createElement('th'); th.textContent = title; $('report-head').append(th);
    }
    tableRows($('report-rows'), reportResult.rows.slice((page - 1) * 10, page * 10), columns.map(c => c[1]));
    pager('report-pager', {total: reportResult.rows.length, page, pages: Math.max(1, Math.ceil(reportResult.rows.length / 10))}, summaryPage);
}
function renderRegisters(registers) {
    $('registers').replaceChildren();
    if (!registers.length) $('registers').textContent = 'No records to display.';
    for (const register of registers) {
        const section = document.createElement('details'); section.className = 'register';
        section.open = registers.indexOf(register) === 0;
        const heading = document.createElement('summary');
        heading.textContent = moduleLabel(register.code) + ' · ' + register.year + ' · ' + register.rows.length + ' students';
        const lecturer = document.createElement('p'); lecturer.className = 'muted';
        lecturer.textContent = 'Lecturer: ' + (register.lecturers.join(', ') || 'Not assigned');
        const wrap = document.createElement('div'); wrap.className = 'table-wrap';
        const table = document.createElement('table'), head = document.createElement('thead');
        const titles = document.createElement('tr'), body = document.createElement('tbody');
        for (const title of ['Registration No.', 'Name', ...register.sessions.map(s => 'W' + s.week + ' · ' + s.date),
            'Present', 'Absent', 'MC', 'Special Medical', 'Excused', 'Total Sessions', 'Attendance %', 'Eligibility']) {
            const cell = document.createElement('th'); cell.textContent = title; titles.append(cell);
        }
        head.append(titles); table.append(head, body); wrap.append(table);
        const controls = document.createElement('div'); controls.className = 'pager';
        function draw(page = 1) {
            tableRows(body, register.rows.slice((page - 1) * 10, page * 10), [r => r.reg, r => r.name,
                ...register.sessions.map((s, index) => r => r.marks[index]),
                r => r.present, r => r.absent, r => r.medical, r => r.special, r => r.excused,
                r => r.total, percentage, r => r.eligibility]);
            controls.replaceChildren();
            const text = document.createElement('span'); text.textContent = 'Page ' + page + ' of ' + Math.max(1, Math.ceil(register.rows.length / 10));
            controls.append(text);
            for (const [title, step] of [['Previous', -1], ['Next', 1]]) {
                const button = document.createElement('button'); button.className = 'secondary'; button.textContent = title;
                button.disabled = step < 0 ? page <= 1 : page * 10 >= register.rows.length;
                button.onclick = () => draw(page + step); controls.append(button);
            }
        }
        draw(); section.append(heading, lecturer, wrap, controls); $('registers').append(section);
    }
    $('register-preview').hidden = false;
}
async function viewReport(course = '') {
    clearReport(); const version = reportVersion;
    const query = reportParams(course), body = reportStaff ? selectedBody() : {};
    reportBusy = true; if (reportStaff) selectionCount();
    try {
        const result = await api('/api/report?' + query, body);
        const detail = await api('/api/report-view?' + query, body);
        if (version !== reportVersion) return;
        reportResult = result;
        $('report-title').textContent = 'Report Summary';
        $('report-description').textContent = $('report-year').value + (course ? ' · ' + moduleLabel(course.split('~')[0]) : '');
        summaryPage(); $('report-results').hidden = false; renderRegisters(detail.registers);
        const missing = result.rows.reduce((n, r) => n + Number(r.unmarked || 0), 0);
        if (missing) message('report-message', missing + ' student-session records are unmarked.');
    } catch (error) {
        if (version === reportVersion) message('report-message', error.message, true);
    } finally { reportBusy = false; if (reportStaff) selectionCount(); }
}
async function downloadReport(course = '', separate = false) {
    const query = reportParams(course) + (separate ? '&type=single' : '');
    let body = reportStaff ? selectedBody() : {};
    if (separate) body = {registrations: [...selectedStudents]};
    reportBusy = true; if (reportStaff) selectionCount();
    try {
        const response = await fetch((separate ? '/api/student-reports.zip?' : '/api/report.xlsx?') + query, {
            method: 'POST', headers: {'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content}, body: JSON.stringify(body)
        });
        if (!response.ok) { const error = await response.json(); throw new Error(error.error || 'Download failed.'); }
        const url = URL.createObjectURL(await response.blob()), link = document.createElement('a');
        link.href = url; link.download = separate ? 'student-attendance-reports.zip' : 'attendance-report.xlsx'; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { message('report-message', error.message, true); }
    finally { reportBusy = false; if (reportStaff) selectionCount(); }
}
function lecturerModules() {
    clearReport(); $('assigned-modules').replaceChildren();
    const courses = reportOptions.courses.filter(c => {
        const [year, study, semester] = c.semester.split('|');
        return year === $('report-year').value && (!$('report-semester').value || semester === $('report-semester').value);
    });
    if (!courses.length) $('assigned-modules').textContent = 'No assigned modules for this selection.';
    for (const course of courses) {
        const card = document.createElement('section'); card.className = 'card';
        const title = document.createElement('h2'); title.textContent = moduleLabel(course.code.split('~')[0]);
        const caption = document.createElement('p'); caption.className = 'muted'; caption.textContent = 'All enrolled students';
        const actions = document.createElement('div'); actions.className = 'actions';
        for (const [label, action] of [['View Report', () => viewReport(course.code)], ['Download Excel', () => downloadReport(course.code)]]) {
            const button = document.createElement('button'); button.textContent = label; button.onclick = action; actions.append(button);
        }
        card.append(title, caption, actions); $('assigned-modules').append(card);
    }
}
if (reportStaff) {
    $('view-report').onclick = () => viewReport(); $('download').onclick = () => downloadReport();
    $('download-students').onclick = () => downloadReport('', true);
    $('student-search').oninput = () => studentPage();
    $('select-all').onchange = () => {
        selectedStudents = new Set($('select-all').checked ? reportStudents.map(r => r.reg) : []);
        clearReport(); selectionCount(); studentPage();
    };
    $('report-batch').onchange = loadReportStudents;
}
for (const id of ['report-year', 'report-semester']) $(id).onchange = reportStaff ? loadReportStudents : lecturerModules;
(async () => {
    try {
        reportOptions = await api('/api/options');
        const years = [...new Set(reportOptions.semesters.map(s => s.id.split('|')[0]))].sort().reverse();
        fillSelect('report-year', years, r => r, r => r, 'Select academic year');
        if (years.length) $('report-year').value = years[0];
        if (reportStaff) {
            fillSelect('report-batch', reportOptions.batches, r => r, r => r, 'All batches');
            await loadReportStudents();
        } else lecturerModules();
    } catch (error) { message('report-message', error.message, true); }
})();
