(function () {
    function parseEditorData(rawValue) {
        if (!rawValue) return { blocks: [] };
        try {
            return JSON.parse(rawValue);
        } catch (error) {
            return { blocks: [] };
        }
    }

    function getCookie(name) {
        const cookieValue = document.cookie
            .split(";")
            .map((item) => item.trim())
            .find((item) => item.startsWith(name + "="));
        return cookieValue ? decodeURIComponent(cookieValue.split("=").slice(1).join("=")) : "";
    }

    function buildImageUploader(uploadUrl) {
        return {
            async uploadByFile(file) {
                const formData = new FormData();
                formData.append("image", file);

                const response = await fetch(uploadUrl, {
                    method: "POST",
                    body: formData,
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken"),
                    },
                    credentials: "same-origin",
                });

                const payload = await response.json();
                if (!response.ok || !payload.success) {
                    throw new Error(payload.message || "Image upload failed.");
                }
                return payload;
            },
        };
    }

    function buildTools(uploadUrl) {
        const listTool = window.EditorjsList || window.List;
        const tools = {};

        if (window.Header) tools.header = window.Header;
        if (listTool) tools.list = listTool;
        if (window.Checklist) tools.checklist = window.Checklist;
        if (window.Quote) tools.quote = window.Quote;
        if (window.Table) tools.table = window.Table;
        if (window.CodeTool) tools.code = window.CodeTool;
        if (window.Delimiter) tools.delimiter = window.Delimiter;
        if (window.Embed) tools.embed = window.Embed;
        if (window.ImageTool && uploadUrl) {
            tools.image = {
                class: window.ImageTool,
                config: {
                    uploader: buildImageUploader(uploadUrl),
                },
            };
        }

        return tools;
    }

    window.initCmsEditors = function (config) {
        if (!window.EditorJS) return [];

        const form = document.getElementById(config.formId);
        if (!form) return [];

        const editors = [];
        for (const editorConfig of config.editors || []) {
            const input = document.getElementById(editorConfig.inputId);
            const holder = document.getElementById(editorConfig.holderId);
            if (!input || !holder) continue;

            const editor = new window.EditorJS({
                holder: editorConfig.holderId,
                data: parseEditorData(input.value),
                placeholder: editorConfig.placeholder || "",
                tools: buildTools(config.uploadUrl),
            });

            editors.push({ editor: editor, input: input });
        }

        form.addEventListener("submit", async function (event) {
            event.preventDefault();
            try {
                for (const item of editors) {
                    const output = await item.editor.save();
                    item.input.value = JSON.stringify(output);
                }
                form.submit();
            } catch (error) {
                console.error("Editor.js save error", error);
                alert(error.message || "Unable to save editor content. Check browser console for details.");
            }
        });

        return editors;
    };
})();
