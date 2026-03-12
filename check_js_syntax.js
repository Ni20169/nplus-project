// 提取自 project_master_list.html 的 JavaScript 代码

// 全局函数定义，确保 onclick 可以调用
function showAddForm() {
    document.getElementById('addForm').style.display = 'block';
    document.getElementById('searchForm').style.display = 'none';
    document.getElementById('updatePanel').style.display = 'none';
    document.getElementById('approvalPanel').style.display = 'none';
    document.querySelector('.data-table').style.display = 'none';
}

function hideAddForm() {
    document.getElementById('addForm').style.display = 'none';
}

function showApprovalPanel() {
    document.getElementById('approvalPanel').style.display = 'block';
    document.getElementById('addForm').style.display = 'none';
    document.getElementById('searchForm').style.display = 'none';
    document.getElementById('updatePanel').style.display = 'none';
    document.querySelector('.data-table').style.display = 'block';
}

function hideApprovalPanel() {
    document.getElementById('approvalPanel').style.display = 'none';
}

function submitDeleteApproval(projectCode, projectName) {
    const note = prompt(`确定要删除项目 "${projectName}" (${projectCode}) 吗？\n\n请输入删除说明（选填）：`);
    if (note === null) return;

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/submit_delete_approval';
    form.style.display = 'none';

    const csrfToken = document.createElement('input');
    csrfToken.type = 'hidden';
    csrfToken.name = 'csrfmiddlewaretoken';
    csrfToken.value = 'test_token';
    form.appendChild(csrfToken);

    const codeInput = document.createElement('input');
    codeInput.type = 'hidden';
    codeInput.name = 'project_code';
    codeInput.value = projectCode;
    form.appendChild(codeInput);

    const noteInput = document.createElement('input');
    noteInput.type = 'hidden';
    noteInput.name = 'change_note';
    noteInput.value = note;
    form.appendChild(noteInput);

    document.body.appendChild(form);
    form.submit();
}

function showSearchForm() {
    document.getElementById('searchForm').style.display = 'block';
    document.getElementById('addForm').style.display = 'none';
    document.getElementById('updatePanel').style.display = 'none';
    document.getElementById('approvalPanel').style.display = 'none';
    document.querySelector('.data-table').style.display = 'block';
    document.getElementById('searchForm').classList.remove('collapsed');
    const toggleBtn = document.getElementById('toggleSearchFields');
    if (toggleBtn) {
        toggleBtn.textContent = '收起';
    }
}

function showUpdatePanel() {
    document.getElementById('updatePanel').style.display = 'block';
    document.getElementById('addForm').style.display = 'none';
    document.getElementById('searchForm').style.display = 'none';
    document.getElementById('approvalPanel').style.display = 'none';
    document.querySelector('.data-table').style.display = 'none';
    document.getElementById('updatePanel').classList.remove('collapsed');
    const toggleBtn = document.getElementById('toggleUpdatePanel');
    if (toggleBtn) {
        toggleBtn.textContent = '收起';
    }
}

function hideSearchForm() {
    document.getElementById('searchForm').style.display = 'none';
}

function hideUpdatePanel() {
    document.getElementById('updatePanel').style.display = 'none';
}

function toggleSubMenu(id, triggerEl) {
    const target = document.getElementById(id);
    if (target) {
        const isOpen = target.classList.toggle('show');
        if (triggerEl) {
            triggerEl.classList.toggle('open', isOpen);
        }
    }
}

function refreshList() {
    document.getElementById('addForm').style.display = 'none';
    document.getElementById('searchForm').style.display = 'none';
    document.getElementById('updatePanel').style.display = 'none';
    document.getElementById('approvalPanel').style.display = 'none';
    document.querySelector('.data-table').style.display = 'block';
}

// 模拟 DOMContentLoaded 事件
function mockDOMContentLoaded() {
    // 信息更新页签联动逻辑
    const updateCodeSelect = document.getElementById('updateCodeSelect');
    const updateNameSelect = document.getElementById('updateNameSelect');
    const updateTargetSelect = document.getElementById('updateTargetSelect');
    
    if (updateCodeSelect && updateTargetSelect) {
        updateCodeSelect.addEventListener('change', function() {
            const selectedCode = this.value;
            if (selectedCode) {
                updateTargetSelect.value = selectedCode;
            } else {
                updateTargetSelect.value = '';
            }
        });
    }
    
    if (updateNameSelect && updateTargetSelect) {
        updateNameSelect.addEventListener('change', function() {
            const selectedName = this.value;
            if (selectedName) {
                for (let option of updateTargetSelect.options) {
                    if (option.text.includes(selectedName)) {
                        updateTargetSelect.value = option.value;
                        break;
                    }
                }
            } else {
                updateTargetSelect.value = '';
            }
        });
    }

    document.querySelectorAll('.menu-toggle').forEach((toggle) => {
        const targetId = toggle.getAttribute('data-target');
        const target = document.getElementById(targetId);
        if (target && target.classList.contains('show')) {
            toggle.classList.add('open');
        }
        toggle.addEventListener('click', () => {
            if (!target) return;
            const isOpen = target.classList.toggle('show');
            toggle.classList.toggle('open', isOpen);
        });
    });

    const layoutRoot = document.getElementById('layoutRoot');
    const toggleSidebarBtn = document.getElementById('toggleSidebar');
    if (toggleSidebarBtn) {
        toggleSidebarBtn.addEventListener('click', () => {
            layoutRoot.classList.toggle('sidebar-hidden');
            toggleSidebarBtn.textContent = layoutRoot.classList.contains('sidebar-hidden') ? '显示菜单' : '隐藏菜单';
        });
    }

    const toggleSearchFields = document.getElementById('toggleSearchFields');
    if (toggleSearchFields) {
        toggleSearchFields.addEventListener('click', () => {
            const form = document.getElementById('searchForm');
            form.classList.toggle('collapsed');
            toggleSearchFields.textContent = form.classList.contains('collapsed') ? '展开' : '收起';
        });
    }

    const toggleUpdatePanel = document.getElementById('toggleUpdatePanel');
    if (toggleUpdatePanel) {
        toggleUpdatePanel.addEventListener('click', () => {
            const panel = document.getElementById('updatePanel');
            panel.classList.toggle('collapsed');
            toggleUpdatePanel.textContent = panel.classList.contains('collapsed') ? '展开' : '收起';
        });
    }

    // 使用之前声明的 updateTargetSelect 变量
    if (updateTargetSelect) {
        updateTargetSelect.addEventListener('change', () => {
            if (updateTargetSelect.value) {
                updateTargetSelect.form.submit();
            }
        });
    }

    const addUpdateRowBtn = document.getElementById('addUpdateRow');
    const updateTemplates = document.getElementById('updateFieldTemplates');
    const requiredUpdateFields = new Set([
        'project_name',
        'province_code',
        'business_unit',
        'dept',
        'project_type',
        'org_mode',
        'data_status',
        'is_execution_level',
        'status'
    ]);

    function applyUpdateFieldTemplate(row) {
        const keySelect = row.querySelector('.update-field-key');
        const valueCell = row.querySelector('.update-value-cell');
        if (!keySelect || !valueCell) return;
        const fieldKey = keySelect.value;
        let control = null;
        if (updateTemplates) {
            const template = updateTemplates.querySelector(`[data-field="${fieldKey}"]`);
            if (template) {
                control = template.cloneNode(true);
            }
        }
        valueCell.innerHTML = '<label>新值</label>';
        if (!control) {
            const input = document.createElement('input');
            input.type = 'text';
            input.name = 'update_field_value';
            input.placeholder = '填写新值';
            control = input;
        }
        control.name = 'update_field_value';
        if (requiredUpdateFields.has(fieldKey)) {
            control.required = true;
        }
        valueCell.appendChild(control);
    }

    if (addUpdateRowBtn) {
        addUpdateRowBtn.addEventListener('click', function() {
            const tableBody = document.querySelector('#updateFieldsTable tbody');
            if (!tableBody) return;
            const newRow = document.createElement('tr');
            newRow.innerHTML = `
                <td>
                    <select class="update-field-key" name="update_field_key">
                        <option value="">选择字段</option>
                        <option value="project_name">项目名称</option>
                        <option value="province_code">所在省</option>
                        <option value="business_unit">业务板块</option>
                        <option value="dept">项目承担部门</option>
                        <option value="project_type">项目类型</option>
                        <option value="org_mode">项目组织模式</option>
                        <option value="data_status">主数据系统数据状态</option>
                        <option value="is_execution_level">是否为执行层</option>
                        <option value="status">状态</option>
                    </select>
                </td>
                <td class="update-value-cell"><label>新值</label></td>
                <td><button type="button" class="remove-row-btn">删除</button></td>
            `;
            tableBody.appendChild(newRow);
            applyUpdateFieldTemplate(newRow);
            newRow.querySelector('.remove-row-btn').addEventListener('click', function() {
                newRow.remove();
            });
            newRow.querySelector('.update-field-key').addEventListener('change', function() {
                applyUpdateFieldTemplate(newRow);
            });
        });
    }

    document.querySelectorAll('#updateFieldsTable .update-field-key').forEach((select) => {
        select.addEventListener('change', function() {
            const row = this.closest('tr');
            applyUpdateFieldTemplate(row);
        });
    });

    document.querySelectorAll('#updateFieldsTable .remove-row-btn').forEach((btn) => {
        btn.addEventListener('click', function() {
            this.closest('tr').remove();
        });
    });

    const table = document.querySelector('.data-table table');
    if (table) {
        const thead = table.querySelector('thead');
        if (thead) {
            const headers = thead.querySelectorAll('th');
            let sortIndex = -1;
            let sortAsc = true;
            headers.forEach((header, index) => {
                if (header.classList.contains('sortable')) {
                    header.style.cursor = 'pointer';
                    header.addEventListener('click', () => {
                        sortAsc = sortIndex === index ? !sortAsc : true;
                        sortIndex = index;
                        const tbody = table.querySelector('tbody');
                        const rows = Array.from(tbody.querySelectorAll('tr'));
                        rows.sort((a, b) => {
                            const aText = a.children[index]?.textContent.trim() || '';
                            const bText = b.children[index]?.textContent.trim() || '';
                            if (!aText && !bText) return 0;
                            if (!aText) return sortAsc ? 1 : -1;
                            if (!bText) return sortAsc ? -1 : 1;
                            if (aText === bText) return 0;
                            return sortAsc ? aText.localeCompare(bText, 'zh-Hans-CN') : bText.localeCompare(aText, 'zh-Hans-CN');
                        });
                        rows.forEach((row) => tbody.appendChild(row));
                    });
                }
            });
        }
    }

    function applyFilters() {
        const table = document.querySelector('.data-table table');
        if (!table) return;
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');
        const filters = {
            code: document.getElementById('searchCode')?.value.toLowerCase() || '',
            name: document.getElementById('searchName')?.value.toLowerCase() || '',
            org: document.getElementById('searchOrg')?.value.toLowerCase() || '',
            parent: document.getElementById('searchParentCode')?.value.toLowerCase() || '',
            creator: document.getElementById('searchCreator')?.value.toLowerCase() || ''
        };
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            const code = cells[1]?.textContent.toLowerCase() || '';
            const name = cells[2]?.textContent.toLowerCase() || '';
            const org = cells[3]?.textContent.toLowerCase() || '';
            const parent = cells[4]?.textContent.toLowerCase() || '';
            const creator = cells[12]?.textContent.toLowerCase() || '';
            const matches = (
                code.includes(filters.code) &&
                name.includes(filters.name) &&
                org.includes(filters.org) &&
                parent.includes(filters.parent) &&
                creator.includes(filters.creator)
            );
            row.style.display = matches ? '' : 'none';
        });
    }

    document.getElementById('searchCode')?.addEventListener('input', applyFilters);
    document.getElementById('searchName')?.addEventListener('input', applyFilters);
    document.getElementById('searchOrg')?.addEventListener('input', applyFilters);
    document.getElementById('searchParentCode')?.addEventListener('input', applyFilters);
    document.getElementById('searchCreator')?.addEventListener('input', applyFilters);

    applyFilters();
}

console.log('JavaScript syntax check passed!');
