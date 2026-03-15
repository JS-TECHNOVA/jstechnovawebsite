(function () {
    function getCookie(name) {
        const cookieValue = document.cookie
            .split(";")
            .map((item) => item.trim())
            .find((item) => item.startsWith(name + "="));
        return cookieValue ? decodeURIComponent(cookieValue.split("=").slice(1).join("=")) : "";
    }

    function formatBytes(value) {
        const bytes = Number(value || 0);
        if (!bytes) return "0 B";
        const units = ["B", "KB", "MB", "GB"];
        let size = bytes;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex += 1;
        }
        return (size >= 10 || unitIndex === 0 ? Math.round(size) : size.toFixed(1)) + " " + units[unitIndex];
    }

    function createButton(label, extraClass) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = extraClass;
        button.textContent = label;
        return button;
    }

    function buildAcceptValue(types) {
        const accepted = [];
        if (types.includes("image")) {
            accepted.push(".jpg", ".jpeg", ".png", ".gif", ".webp");
        }
        if (types.includes("video")) {
            accepted.push(".mp4", ".m4v", ".mov", ".webm");
        }
        if (types.includes("file")) {
            accepted.push(".pdf", ".docx", ".xlsx", ".pptx");
        }
        return accepted.join(",");
    }

    function isAllowedAssetType(assetType, types) {
        return !types.length || types.includes(assetType);
    }

    function buildPreviewContent(value, types) {
        if (!value) {
            return "<p class='text-xs text-slate-500'>No media selected.</p>";
        }

        const typeList = (types || "").split(",");
        if (typeList.includes("image")) {
            return (
                "<div class='flex min-w-0 max-w-full items-center gap-3 overflow-hidden'>" +
                "<img src='" + value + "' alt='' class='h-12 w-12 rounded-xl object-cover ring-1 ring-slate-200'>" +
                "<a href='" + value + "' target='_blank' rel='noopener' class='min-w-0 max-w-full truncate text-xs font-semibold text-blue-600 hover:text-blue-700'>" +
                value +
                "</a></div>"
            );
        }

        return (
            "<div class='flex min-w-0 max-w-full items-center gap-3 overflow-hidden'>" +
            "<span class='grid h-12 w-12 place-items-center rounded-xl bg-slate-100 text-slate-500 ring-1 ring-slate-200'><i class='fa-solid fa-paperclip'></i></span>" +
            "<a href='" + value + "' target='_blank' rel='noopener' class='min-w-0 max-w-full truncate text-xs font-semibold text-blue-600 hover:text-blue-700'>" +
            value +
            "</a></div>"
        );
    }

    function initFieldPicker(field, modal) {
        const actionRow = document.createElement("div");
        actionRow.className = "mt-3 flex flex-wrap items-center gap-2";

        const pickButton = createButton(
            "Pick media",
            "inline-flex items-center justify-center rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-white transition hover:bg-slate-700"
        );
        const clearButton = createButton(
            "Clear",
            "inline-flex items-center justify-center rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600 transition hover:bg-slate-50"
        );
        const preview = document.createElement("div");
        preview.className = "mt-3 min-w-0 max-w-full overflow-hidden rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3";

        actionRow.appendChild(pickButton);
        actionRow.appendChild(clearButton);
        field.insertAdjacentElement("afterend", actionRow);
        actionRow.insertAdjacentElement("afterend", preview);

        function renderPreview() {
            preview.innerHTML = buildPreviewContent(field.value, field.dataset.mediaTypes || "");
        }

        renderPreview();

        pickButton.addEventListener("click", function () {
            modal.open(field);
        });

        clearButton.addEventListener("click", function () {
            field.value = "";
            field.dispatchEvent(new Event("input", { bubbles: true }));
            field.dispatchEvent(new Event("change", { bubbles: true }));
            renderPreview();
        });

        field.addEventListener("input", renderPreview);
        field.addEventListener("change", renderPreview);
    }

    function initMediaPickerModal() {
        const root = document.getElementById("cmsMediaPicker");
        if (!root) return null;

        const backdrop = root.querySelector("[data-media-picker-backdrop]");
        const panel = root.querySelector("[data-media-picker-panel]");
        const libraryUrl = root.dataset.libraryUrl || "/cms/media/library-data/";
        const uploadUrl = root.dataset.uploadUrl || "/cms/media/upload-file/";
        const closeButtons = root.querySelectorAll("[data-media-picker-close]");
        const searchInput = document.getElementById("mediaPickerSearch");
        const countNode = document.getElementById("mediaPickerCount");
        const targetLabel = document.getElementById("mediaPickerTargetLabel");
        const grid = document.getElementById("mediaPickerGrid");
        const uploadInput = document.getElementById("mediaPickerUploadInput");
        const optimizeInput = document.getElementById("mediaPickerOptimize");
        const uploadFeedback = document.getElementById("mediaPickerUploadFeedback");
        const filterButtons = Array.from(root.querySelectorAll("[data-media-filter]"));

        const state = {
            field: null,
            types: [],
            filter: "all",
            search: "",
        };

        function setVisible(visible) {
            if (visible) {
                root.classList.remove("hidden", "pointer-events-none");
                requestAnimationFrame(function () {
                    backdrop.classList.remove("opacity-0");
                    panel.classList.remove("translate-y-6", "opacity-0");
                });
                document.body.classList.add("overflow-hidden");
            } else {
                backdrop.classList.add("opacity-0");
                panel.classList.add("translate-y-6", "opacity-0");
                setTimeout(function () {
                    root.classList.add("hidden", "pointer-events-none");
                }, 200);
                document.body.classList.remove("overflow-hidden");
            }
        }

        function updateFilterButtons() {
            filterButtons.forEach(function (button) {
                const active = button.dataset.mediaFilter === state.filter;
                button.className = active
                    ? "rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-white"
                    : "rounded-full border border-slate-300 bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600";
            });
        }

        function buildCard(asset) {
            const wrapper = document.createElement("article");
            wrapper.className = "overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-sm";

            let previewMarkup = "";
            if (asset.asset_type === "image") {
                previewMarkup = "<img src='" + asset.url + "' alt='' class='h-40 w-full object-cover'>";
            } else if (asset.asset_type === "video") {
                previewMarkup = "<video src='" + asset.url + "' class='h-40 w-full bg-slate-950 object-cover' muted playsinline preload='metadata'></video>";
            } else {
                previewMarkup =
                    "<div class='flex h-40 items-center justify-center bg-slate-50 text-slate-400'>" +
                    "<div class='text-center'><i class='fa-regular fa-file-lines text-4xl'></i>" +
                    "<p class='mt-3 text-xs font-semibold uppercase tracking-[0.18em]'>" + (asset.extension || "FILE") + "</p></div></div>";
            }

            wrapper.innerHTML =
                previewMarkup +
                "<div class='space-y-3 p-4'>" +
                "<div class='flex items-center justify-between gap-3'>" +
                "<span class='rounded-full bg-slate-100 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500'>" + asset.asset_type + "</span>" +
                (asset.is_optimized ? "<span class='rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-600'>optimized</span>" : "") +
                "</div>" +
                "<div><p class='truncate text-sm font-bold text-slate-900'>" + (asset.title || asset.original_name) + "</p>" +
                "<p class='mt-1 truncate text-xs text-slate-500'>" + asset.original_name + "</p></div>" +
                "<div class='flex items-center justify-between gap-3 text-xs text-slate-400'>" +
                "<span>" + formatBytes(asset.file_size) + "</span>" +
                "<span>" + new Date(asset.created_at).toLocaleDateString() + "</span>" +
                "</div>" +
                "<div class='flex gap-2'>" +
                "<button type='button' class='media-select flex-1 rounded-full bg-blue-600 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-white transition hover:bg-blue-700'>Select</button>" +
                "<a href='" + asset.url + "' target='_blank' rel='noopener' class='inline-flex items-center justify-center rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600 transition hover:bg-slate-50'>Open</a>" +
                "</div></div>";

            wrapper.querySelector(".media-select").addEventListener("click", function () {
                if (!state.field) return;
                if (!isAllowedAssetType(asset.asset_type, state.types)) return;
                state.field.value = asset.url;
                state.field.dispatchEvent(new Event("input", { bubbles: true }));
                state.field.dispatchEvent(new Event("change", { bubbles: true }));
                setVisible(false);
            });

            return wrapper;
        }

        async function loadAssets() {
            grid.innerHTML = "<div class='col-span-full rounded-[20px] border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600'>Loading media...</div>";
            const params = new URLSearchParams();
            if (state.search) params.set("q", state.search);
            if (state.filter !== "all") {
                params.set("type", state.filter);
            } else if (state.types.length) {
                params.set("types", state.types.join(","));
            }

            const response = await fetch(libraryUrl + "?" + params.toString(), {
                credentials: "same-origin",
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const payload = await response.json();
            const assets = payload.assets || [];
            grid.innerHTML = "";
            countNode.textContent = assets.length + " items";

            if (!assets.length) {
                grid.innerHTML = "<div class='col-span-full rounded-[20px] border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600'>No media found for this filter.</div>";
                return;
            }

            assets.forEach(function (asset) {
                grid.appendChild(buildCard(asset));
            });
        }

        async function uploadAsset(file) {
            const formData = new FormData();
            formData.append("file", file);
            if (optimizeInput && optimizeInput.checked) {
                formData.append("optimize", "true");
            }

            uploadFeedback.className = "mt-4 rounded-[18px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600";
            uploadFeedback.textContent = "Uploading media...";
            uploadFeedback.classList.remove("hidden");

            const response = await fetch(uploadUrl, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                },
            });
            const payload = await response.json();
            if (!response.ok || !payload.success) {
                throw new Error(payload.message || "Upload failed.");
            }

            uploadFeedback.className = "mt-4 rounded-[18px] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700";
            uploadFeedback.textContent = "Media uploaded to library.";
            await loadAssets();
            return payload.asset;
        }

        if (searchInput) {
            let searchTimer = null;
            searchInput.addEventListener("input", function () {
                state.search = searchInput.value.trim();
                clearTimeout(searchTimer);
                searchTimer = setTimeout(loadAssets, 180);
            });
        }

        filterButtons.forEach(function (button) {
            button.addEventListener("click", function () {
                state.filter = button.dataset.mediaFilter || "all";
                updateFilterButtons();
                loadAssets();
            });
        });

        if (uploadInput) {
            uploadInput.addEventListener("change", async function () {
                const file = uploadInput.files && uploadInput.files[0];
                if (!file) return;
                try {
                    const uploadedAsset = await uploadAsset(file);
                    if (
                        state.field &&
                        uploadedAsset &&
                        uploadedAsset.url &&
                        isAllowedAssetType(uploadedAsset.asset_type, state.types)
                    ) {
                        state.field.value = uploadedAsset.url;
                        state.field.dispatchEvent(new Event("input", { bubbles: true }));
                        state.field.dispatchEvent(new Event("change", { bubbles: true }));
                    } else if (uploadedAsset && !isAllowedAssetType(uploadedAsset.asset_type, state.types)) {
                        uploadFeedback.className = "mt-4 rounded-[18px] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700";
                        uploadFeedback.textContent = "Upload saved to the library, but this field only accepts " + (state.types.join(", ") || "specific") + " media.";
                        uploadFeedback.classList.remove("hidden");
                    }
                } catch (error) {
                    uploadFeedback.className = "mt-4 rounded-[18px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700";
                    uploadFeedback.textContent = error.message || "Upload failed.";
                    uploadFeedback.classList.remove("hidden");
                } finally {
                    uploadInput.value = "";
                }
            });
        }

        closeButtons.forEach(function (button) {
            button.addEventListener("click", function () {
                setVisible(false);
            });
        });
        if (backdrop) {
            backdrop.addEventListener("click", function () {
                setVisible(false);
            });
        }

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && !root.classList.contains("hidden")) {
                setVisible(false);
            }
        });

        updateFilterButtons();

        return {
            open: function (field) {
                state.field = field;
                state.types = (field.dataset.mediaTypes || "image").split(",").filter(Boolean);
                state.filter = state.types.length === 1 ? state.types[0] : "all";
                state.search = "";
                if (searchInput) searchInput.value = "";
                if (uploadInput) {
                    const acceptValue = buildAcceptValue(state.types);
                    if (acceptValue) {
                        uploadInput.setAttribute("accept", acceptValue);
                    } else {
                        uploadInput.removeAttribute("accept");
                    }
                }
                if (uploadFeedback) uploadFeedback.classList.add("hidden");
                if (targetLabel) {
                    targetLabel.textContent = "Select media for " + (field.dataset.mediaPickerLabel || field.name || "field");
                }
                updateFilterButtons();
                setVisible(true);
                loadAssets();
            },
        };
    }

    document.addEventListener("DOMContentLoaded", function () {
        const modal = initMediaPickerModal();
        if (!modal) return;
        document.querySelectorAll("[data-media-picker='true']").forEach(function (field) {
            initFieldPicker(field, modal);
        });
    });
})();
