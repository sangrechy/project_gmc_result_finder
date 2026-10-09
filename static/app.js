document.addEventListener("DOMContentLoaded", () => {
    const themeToggle = document.getElementById("themeToggle");
    const savedTheme = localStorage.getItem("nm-theme") || "light";
    if (savedTheme === "dark") {
        document.documentElement.setAttribute("data-theme", "dark");
        if (themeToggle) themeToggle.textContent = "☀️";
    }

    themeToggle?.addEventListener("click", () => {
        const isDark = document.documentElement.getAttribute("data-theme") === "dark";
        if (isDark) {
            document.documentElement.removeAttribute("data-theme");
            localStorage.setItem("nm-theme", "light");
            themeToggle.textContent = "🌓";
        } else {
            document.documentElement.setAttribute("data-theme", "dark");
            localStorage.setItem("nm-theme", "dark");
            themeToggle.textContent = "☀️";
        }
    });

    function setupSwitch(switchEl) {
        if (!switchEl) return;
        const toggle = () => {
            const isChecked = switchEl.classList.toggle("checked");
            switchEl.setAttribute("aria-checked", isChecked ? "true" : "false");
        };
        switchEl.addEventListener("click", toggle);
        switchEl.addEventListener("keydown", (e) => {
            if (e.key === " " || e.key === "Enter") {
                e.preventDefault();
                toggle();
            }
        });
    }

    const refreshToggle = document.getElementById("refreshToggle");
    const batchRefreshToggle = document.getElementById("batchRefreshToggle");

    setupSwitch(refreshToggle);
    setupSwitch(batchRefreshToggle);

    const navButtons = document.querySelectorAll(".nav-tab-btn");
    const tabPanes = document.querySelectorAll(".tab-content");

    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab");
            navButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            const targetPane = document.getElementById(targetId);
            if (targetPane) targetPane.classList.add("active");
        });
    });

    const searchForm = document.getElementById("searchForm");
    const regNoInput = document.getElementById("regNoInput");
    const loadingIndicator = document.getElementById("loadingIndicator");
    const errorMessage = document.getElementById("errorMessage");
    const resultContainer = document.getElementById("resultContainer");

    searchForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const regNo = regNoInput.value.trim();
        if (!regNo) return;

        errorMessage.classList.add("hidden");
        resultContainer.classList.add("hidden");
        loadingIndicator.classList.remove("hidden");

        const refresh = refreshToggle ? refreshToggle.classList.contains("checked") : false;

        try {
            const res = await fetch(`/api/result/${encodeURIComponent(regNo)}?refresh=${refresh}`);
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "Unable to retrieve student result.");
            }

            renderStudentResult(data);
        } catch (err) {
            errorMessage.textContent = err.message;
            errorMessage.classList.remove("hidden");
        } finally {
            loadingIndicator.classList.add("hidden");
        }
    });

    function renderStudentResult(data) {
        document.getElementById("studentName").textContent = data.student_name || "N/A";
        document.getElementById("studentReg").textContent = `Reg No: ${data.registration_no || "N/A"}`;
        document.getElementById("studentCollege").textContent = data.institution_name || "N/A";
        document.getElementById("studentCourse").textContent = data.course || "N/A";

        const overallBadge = document.getElementById("overallBadge");
        const isPass = (data.overall_result || "").toUpperCase() === "PASS";
        overallBadge.textContent = data.overall_result || "N/A";
        overallBadge.className = `nm-score-badge ${isPass ? "pass" : "fail"}`;

        document.getElementById("overallMarks").textContent = data.overall_marks ? `${data.overall_marks}%` : "";
        document.getElementById("examSession").textContent = data.exam_session || "N/A";
        document.getElementById("termName").textContent = data.term_name || "N/A";
        document.getElementById("regulation").textContent = data.regulation || "N/A";
        document.getElementById("publishDate").textContent = data.result_published_date || "N/A";

        const subjectsBody = document.getElementById("subjectsBody");
        subjectsBody.innerHTML = "";

        if (Array.isArray(data.subjects)) {
            data.subjects.forEach(subj => {
                const tr = document.createElement("tr");
                let breakdownHtml = "";
                let marksHtml = "";

                if (Array.isArray(subj.papers)) {
                    subj.papers.forEach(p => {
                        const minMax = (p.min_marks || p.max_marks) ? ` <span style="font-size:0.75rem; color:var(--text-muted);">(Min: ${p.min_marks || '-'} / Max: ${p.max_marks || '-'})</span>` : '';
                        breakdownHtml += `<div style="font-size: 0.84rem; margin-bottom: 3px;"><strong>${escapeHtml(p.paper_name)}</strong>${minMax}</div>`;
                        marksHtml += `<div style="font-size: 0.84rem; margin-bottom: 3px; font-weight: 600;">${escapeHtml(p.obtained_mark || "-")}</div>`;
                    });
                }

                const sPass = (subj.result || "").toUpperCase() === "PASS";

                tr.innerHTML = `
                    <td>
                        <strong style="color: var(--text-dark);">${escapeHtml(subj.subject_name || "")}</strong>
                        <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">Code: ${escapeHtml(subj.subject_code || "")}</div>
                    </td>
                    <td>${breakdownHtml || "-"}</td>
                    <td>${marksHtml || "-"}</td>
                    <td><span class="status-pill ${sPass ? "pass" : "fail"}">${escapeHtml(subj.result || "N/A")}</span></td>
                `;
                subjectsBody.appendChild(tr);
            });
        }

        resultContainer.classList.remove("hidden");
    }

    const batchForm = document.getElementById("batchForm");
    const startRegInput = document.getElementById("startReg");
    const endRegInput = document.getElementById("endReg");
    const batchProgress = document.getElementById("batchProgress");
    const progressFill = document.getElementById("progressFill");
    const batchStatusText = document.getElementById("batchStatusText");
    const batchResultsContainer = document.getElementById("batchResultsContainer");
    const batchTableBody = document.getElementById("batchTableBody");
    const batchSummaryStats = document.getElementById("batchSummaryStats");
    const batchErrorMessage = document.getElementById("batchErrorMessage");
    const exportCsvBtn = document.getElementById("exportCsvBtn");
    const exportExcelBtn = document.getElementById("exportExcelBtn");
    const batchPercentBadge = document.getElementById("batchPercentBadge");

    let currentBatchData = [];

    batchForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const start = parseInt(startRegInput.value.trim(), 10);
        const end = parseInt(endRegInput.value.trim(), 10);

        if (isNaN(start) || isNaN(end) || end < start) {
            alert("Please enter a valid start and end registration number.");
            return;
        }

        const count = end - start + 1;
        if (count > 500) {
            alert("Maximum range limit is 500 registration numbers.");
            return;
        }

        batchErrorMessage?.classList.add("hidden");
        batchResultsContainer?.classList.remove("hidden");
        batchTableBody.innerHTML = "";
        currentBatchData = [];

        batchProgress?.classList.remove("hidden");
        progressFill.style.width = "0%";
        if (batchPercentBadge) batchPercentBadge.textContent = "0%";
        batchStatusText.textContent = `0% (0 out of ${count} data collected)`;
        batchSummaryStats.textContent = `Collecting data... 0 out of ${count}`;

        const forceRefresh = batchRefreshToggle ? batchRefreshToggle.classList.contains("checked") : false;
        const streamUrl = `/api/batch/stream?start=${start}&end=${end}&refresh=${forceRefresh}`;

        try {
            const eventSource = new EventSource(streamUrl);

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === "progress") {
                        const pct = data.percent || 0;
                        progressFill.style.width = `${pct}%`;
                        if (batchPercentBadge) batchPercentBadge.textContent = `${pct}%`;
                        batchStatusText.textContent = `${pct}% (${data.collected} out of ${data.total} data collected)`;

                        if (data.item) {
                            currentBatchData.push(data.item);
                            appendBatchTableRow(data.item);
                            batchSummaryStats.textContent = `Collecting data: ${data.collected} of ${data.total} (${pct}%)`;
                        }
                    } else if (data.type === "complete") {
                        progressFill.style.width = "100%";
                        if (batchPercentBadge) batchPercentBadge.textContent = "100%";
                        batchStatusText.textContent = `100% (${data.total} out of ${data.total} data collected)`;
                        batchSummaryStats.textContent = `Completed: 100% (${data.total} out of ${data.total} data collected) | Passed: ${data.successful_count} | Failed/Unpublished: ${data.failed_count}`;
                        eventSource.close();
                        setTimeout(() => {
                            batchProgress?.classList.add("hidden");
                        }, 1200);
                    }
                } catch (parseErr) {
                    console.error(parseErr);
                }
            };

            eventSource.onerror = async () => {
                eventSource.close();

                if (currentBatchData.length === 0) {
                    try {
                        const res = await fetch("/api/batch", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                start_reg_no: start,
                                end_reg_no: end,
                                force_refresh: forceRefresh
                            })
                        });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail || "Batch request failed.");
                        currentBatchData = data.results || [];
                        renderBatchResults(data);
                    } catch (fallbackErr) {
                        if (batchErrorMessage) {
                            batchErrorMessage.textContent = fallbackErr.message;
                            batchErrorMessage.classList.remove("hidden");
                        }
                    } finally {
                        batchProgress?.classList.add("hidden");
                    }
                } else {
                    batchProgress?.classList.add("hidden");
                }
            };

        } catch (err) {
            if (batchErrorMessage) {
                batchErrorMessage.textContent = err.message;
                batchErrorMessage.classList.remove("hidden");
            }
            batchProgress?.classList.add("hidden");
        }
    });

    function appendBatchTableRow(item) {
        const tr = document.createElement("tr");
        const isPass = (item.overall_result || "").toUpperCase() === "PASS";
        const isError = (item.overall_result || "").toUpperCase() === "ERROR";

        let statusClass = isPass ? "pass" : "fail";
        if (isError) statusClass = "fail";

        tr.innerHTML = `
            <td><strong>${escapeHtml(item.registration_no || "")}</strong></td>
            <td>${escapeHtml(item.student_name || "N/A")}</td>
            <td style="font-size: 0.84rem;">${escapeHtml(item.institution_name || "-")}</td>
            <td style="font-size: 0.84rem;">${escapeHtml(item.term_name || "-")}</td>
            <td><span class="status-pill ${statusClass}">${escapeHtml(item.overall_result || "N/A")}</span></td>
            <td><strong>${escapeHtml(item.overall_marks ? item.overall_marks + "%" : "-")}</strong></td>
        `;
        batchTableBody.appendChild(tr);
    }

    function renderBatchResults(data) {
        batchTableBody.innerHTML = "";
        const list = data.results || [];

        batchSummaryStats.textContent = `Completed: 100% (${data.total_requested} out of ${data.total_requested} data collected) | Passed: ${data.successful_count} | Failed/Unpublished: ${data.failed_count}`;

        list.forEach(item => {
            appendBatchTableRow(item);
        });

        batchResultsContainer.classList.remove("hidden");
    }

    exportCsvBtn?.addEventListener("click", async () => {
        if (!currentBatchData.length) return;
        try {
            const res = await fetch("/api/batch/export/csv", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(currentBatchData)
            });
            const blob = await res.blob();
            downloadBlob(blob, "results.csv");
        } catch (e) {
            alert("Error exporting CSV: " + e.message);
        }
    });

    exportExcelBtn?.addEventListener("click", async () => {
        if (!currentBatchData.length) return;
        try {
            const res = await fetch("/api/batch/export/excel", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(currentBatchData)
            });
            const blob = await res.blob();
            downloadBlob(blob, "results.xlsx");
        } catch (e) {
            alert("Error exporting Excel: " + e.message);
        }
    });

    function downloadBlob(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    }

    function escapeHtml(text) {
        if (text === null || text === undefined) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
