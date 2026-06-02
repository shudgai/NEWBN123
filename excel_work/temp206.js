            const sortState = ref({ column: null, order: 'asc' });

            const resetView = async () => {
                sortState.value = { column: null, order: 'asc' };
                selectedRows.value = [];
                await fetchData();
                
                toastMessage.value = `介面已恢復`;
                showToast.value = true;
                setTimeout(() => { showToast.value = false; }, 3000);
            };

            const sortBy = (column) => {
                if (sortState.value.column === column) {
                    sortState.value.order = sortState.value.order === 'asc' ? 'desc' : 'asc';
                } else {
                    sortState.value.column = column;
                    sortState.value.order = 'asc';
                }

                const groups = [];
                let i = 0;
                while (i < tableData.value.length) {
                    const row = tableData.value[i];
                    let endIdx = i;
                    while (endIdx < tableData.value.length - 1) {
                        const curr = tableData.value[endIdx];
                        if (curr.remark && (curr.remark.includes('同下批') || curr.remark.includes('及下批') || curr.remark.includes('一齊'))) {
                            const next = tableData.value[endIdx + 1];
                            if (next.date === row.date && next.client_name === row.client_name) {
                                endIdx++;
                            } else {
                                break;
                            }
                        } else {
                            break;
                        }
                    }
                    groups.push(tableData.value.slice(i, endIdx + 1));
                    i = endIdx + 1;
                }

                // If multiple rows are selected, only sort those groups. Otherwise, sort all groups.
                const hasSelection = selectedRows.value.length > 1;
                
                const groupsToSort = [];
                const indicesToSort = [];

                groups.forEach((group, index) => {
                    if (!hasSelection || group.some(row => selectedRows.value.includes(row.id))) {
                        groupsToSort.push(group);
                        indicesToSort.push(index);
                    }
                });

                groupsToSort.sort((groupA, groupB) => {
                    let valA, valB;
                    
                    if (['amount', 'pieces', 'weight'].includes(column)) {
                        valA = groupA.reduce((sum, r) => sum + (parseFloat(r[column]) || 0), 0);
                        valB = groupB.reduce((sum, r) => sum + (parseFloat(r[column]) || 0), 0);
                    } else {
                        valA = groupA[0][column] || '';
                        valB = groupB[0][column] || '';
                    }

                    let cmp = 0;
                    if (typeof valA === 'number' && typeof valB === 'number') {
                        cmp = valA - valB;
                    } else {
                        cmp = valA.toString().localeCompare(valB.toString(), undefined, { numeric: true, sensitivity: 'base' });
                    }

                    if (cmp !== 0) {
                        return sortState.value.order === 'asc' ? cmp : -cmp;
                    }
                    return 0;
                });

                if (hasSelection) {
                    groupsToSort.forEach(group => {
                        if (group.length > 1) {
                            const originalIds = group.map(r => r.id);
                            const originalRemarks = group.map(r => r.remark);
                            
                            group.sort((rowA, rowB) => {
                                let valA = rowA[column] || '';
                                let valB = rowB[column] || '';
                                let cmp = 0;
                                if (typeof valA === 'number' && typeof valB === 'number') {
                                    cmp = valA - valB;
                                } else {
                                    cmp = valA.toString().localeCompare(valB.toString(), undefined, { numeric: true, sensitivity: 'base' });
                                }
                                if (cmp !== 0) {
                                    return sortState.value.order === 'asc' ? cmp : -cmp;
                                }
                                return 0;
                            });

                            group.forEach((r, i) => {
                                r.id = originalIds[i];
                                r.remark = originalRemarks[i];
                            });
                        }
                    });
                }

                for (let j = 0; j < indicesToSort.length; j++) {
                    groups[indicesToSort[j]] = groupsToSort[j];
                }

                tableData.value = groups.flat();

                if (hasSelection) {
                    groupsToSort.forEach(group => {
                        if (group.length > 1) {
                            recalculateAndSave(group[0]);
                        }
                    });
                }
            };
            
