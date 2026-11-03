/**
 * Master Assistant UI controller.
 *
 * The page is served as plain static files, so no bundler and no framework is
 * involved: this file owns the drag & drop upload, previews the selected files,
 * POSTs them to `/analyze`, and renders the JSON payload into `#results`.
 *
 * NOTE: this file is intentionally dependency-free and is not covered by
 * automated tests; exercise it manually in a browser.
 */

(function () {
  "use strict";

  /* ------------------------------------------------------------------ *
   * Constants
   * ------------------------------------------------------------------ */

  /** Absolute loudness delta (LU) below which a value counts as aligned. */
  var OK_DELTA_DB = 0.5;
  /** Threshold in LU above which an integrated-LUFS delta is flagged. */
  var LUFS_DELTA_THRESHOLD_DB = 2.0;
  /** Threshold in dB above which a true-peak delta is flagged. */
  var TRUE_PEAK_DELTA_THRESHOLD_DB = 1.0;
  /** Threshold in LU above which a loudness-range delta is flagged. */
  var LRA_DELTA_THRESHOLD_DB = 2.0;
  /** Abort the upload after this many milliseconds. */
  var REQUEST_TIMEOUT_MS = 60000;
  /** Extensions accepted by the client-side validation. */
  var ACCEPTED_EXTENSIONS = [".wav", ".flac", ".aiff", ".aif", ".mp3", ".ogg"];

  /** Spectrum chart geometry, in viewBox units. */
  var CHART_WIDTH = 700;
  var CHART_HEIGHT = 300;
  var CHART_PAD_LEFT = 48;
  var CHART_PAD_RIGHT = 16;
  var CHART_PAD_TOP = 40;
  var CHART_PAD_BOTTOM = 36;
  /** Lowest dB value the chart is allowed to display. */
  var CHART_FLOOR_DB = -60;
  var CHART_USER_COLOR = "#2563eb";
  var CHART_REFERENCE_COLOR = "#6b7280";

  /* ------------------------------------------------------------------ *
   * DOM references
   * ------------------------------------------------------------------ */

  var analyzeForm = document.getElementById("analyze-form");
  var dropzoneEl = document.getElementById("dropzone");
  var fileInput = document.getElementById("file-input");
  var previewEl = document.getElementById("preview");
  var previewUserEl = document.getElementById("preview-user");
  var previewReferenceEl = document.getElementById("preview-reference");
  var dawSelect = document.getElementById("daw");
  var submitButton = document.getElementById("submit-button");
  var statusEl = document.getElementById("status");
  var resultsEl = document.getElementById("results");

  /* ------------------------------------------------------------------ *
   * State
   * ------------------------------------------------------------------ */

  var state = {
    userFile: null,
    referenceFile: null,
    userDuration: null,
    referenceDuration: null,
    loading: false,
  };

  /* ------------------------------------------------------------------ *
   * Helpers
   * ------------------------------------------------------------------ */

  /**
   * Escape a value so it can be interpolated into an HTML template string.
   *
   * @param {unknown} value Raw value, coerced to string.
   * @returns {string} HTML-safe string.
   */
  function escapeHtml(value) {
    // Entities are assembled from a single ampersand constant so this source file
    // stays free of pre-escaped output that a naive editor could mangle.
    var amp = String.fromCharCode(38);
    return String(value === null || value === undefined ? "" : value)
      .replace(/&/g, amp + "amp;")
      .replace(/</g, amp + "lt;")
      .replace(/>/g, amp + "gt;")
      .replace(/"/g, amp + "quot;")
      .replace(/'/g, amp + "#39;");
  }

  /**
   * Format a number with a fixed number of decimals, tolerating `null` values.
   *
   * @param {unknown} value Number to format.
   * @param {number} digits Number of decimals.
   * @returns {string} Formatted number, or an em dash when unavailable.
   */
  function formatNumber(value, digits) {
    if (typeof value !== "number" || !isFinite(value)) {
      return "\u2014";
    }
    return value.toFixed(digits);
  }

  /**
   * Format a byte count as megabytes with one decimal.
   *
   * @param {unknown} size File size in bytes.
   * @returns {string} Human readable size, or an em dash when unavailable.
   */
  function formatBytes(size) {
    if (typeof size !== "number" || !isFinite(size) || size < 0) {
      return "\u2014";
    }
    return (size / (1024 * 1024)).toFixed(1) + " MB";
  }

  /**
   * Format a duration in seconds as `mm:ss`.
   *
   * @param {unknown} seconds Duration in seconds.
   * @returns {string} Formatted duration, or an em dash when unavailable.
   */
  function formatDuration(seconds) {
    if (typeof seconds !== "number" || !isFinite(seconds) || seconds <= 0) {
      return "\u2014";
    }
    var total = Math.round(seconds);
    var minutes = Math.floor(total / 60);
    var rest = total % 60;
    return String(minutes).padStart(2, "0") + ":" + String(rest).padStart(2, "0");
  }

  /**
   * Return the lowercased extension of a file name, including the dot.
   *
   * @param {string} name File name.
   * @returns {string} Extension such as `.wav`, or an empty string.
   */
  function fileExtension(name) {
    var text = String(name || "");
    var index = text.lastIndexOf(".");
    return index === -1 ? "" : text.slice(index).toLowerCase();
  }

  /**
   * Tell whether a file has an extension the backend can analyze.
   *
   * @param {File|null} file Candidate file.
   * @returns {boolean} `true` when the extension is supported.
   */
  function isAudioFile(file) {
    return !!file && ACCEPTED_EXTENSIONS.indexOf(fileExtension(file.name)) !== -1;
  }

  /**
   * Read the duration of an audio file through the `<audio>` element.
   *
   * Resolves to `0` when the browser cannot decode the metadata (for example
   * FLAC on Safari, or a corrupted file); the UI then shows an em dash. The
   * object URL is revoked on both the success and the failure path.
   *
   * @param {File} file Audio file selected by the user.
   * @returns {Promise<number>} Duration in seconds, or `0` when unavailable.
   */
  function readDuration(file) {
    return new Promise(function (resolve) {
      var url;
      try {
        url = URL.createObjectURL(file);
      } catch (createError) {
        resolve(0);
        return;
      }

      var audio = new Audio(url);
      var settled = false;

      function finish(seconds) {
        if (settled) {
          return;
        }
        settled = true;
        audio.removeEventListener("loadedmetadata", handleLoaded);
        audio.removeEventListener("error", handleError);
        URL.revokeObjectURL(url);
        resolve(seconds);
      }

      function handleLoaded() {
        var duration = audio.duration;
        var valid = typeof duration === "number" && isFinite(duration) && duration > 0;
        finish(valid ? duration : 0);
      }

      function handleError() {
        finish(0);
      }

      audio.addEventListener("loadedmetadata", handleLoaded);
      audio.addEventListener("error", handleError);
      audio.preload = "metadata";
    });
  }

  /* ------------------------------------------------------------------ *
   * Status helpers
   * ------------------------------------------------------------------ */

  /**
   * Set the status message and its styling.
   *
   * @param {string} message Message to show; an empty string hides the element.
   * @param {boolean} [isError] Whether the message is an error.
   * @returns {void}
   */
  function setStatus(message, isError) {
    statusEl.textContent = message;
    statusEl.className = isError ? "error" : "";
  }

  /**
   * Show the loading status together with an indeterminate progress bar.
   *
   * @returns {void}
   */
  function setLoadingStatus() {
    statusEl.innerHTML =
      '<span class="status-text">Analisi in corso...</span>' +
      '<span class="progress" aria-hidden="true"><span class="progress-bar"></span></span>';
    statusEl.className = "loading";
  }

  /* ------------------------------------------------------------------ *
   * Preview rendering
   * ------------------------------------------------------------------ */

  /**
   * Update the submit button so it is enabled only for two valid files.
   *
   * @returns {void}
   */
  function updateSubmitState() {
    submitButton.disabled = state.loading || !isReady();
  }

  /**
   * Tell whether both slots hold a file with a supported extension.
   *
   * @returns {boolean} `true` when the form can be submitted.
   */
  function isReady() {
    return (
      !!state.userFile &&
      isAudioFile(state.userFile) &&
      !!state.referenceFile &&
      isAudioFile(state.referenceFile)
    );
  }

  /**
   * Render one preview card, including its validity icon and remove button.
   *
   * @param {HTMLElement} element Card container.
   * @param {"user"|"reference"} slot Slot identifier.
   * @param {File|null} file File held by the slot.
   * @param {number|null} duration Duration in seconds, or `null` while loading.
   * @param {string} label Card heading.
   * @returns {void}
   */
  function renderPreviewCard(element, slot, file, duration, label) {
    if (!file) {
      element.className = "preview-card empty";
      element.innerHTML =
        '<p class="preview-label">' +
        escapeHtml(label) +
        "</p>" +
        '<p class="preview-empty">Nessun file selezionato</p>';
      return;
    }

    var valid = isAudioFile(file);
    element.className = "preview-card " + (valid ? "valid" : "invalid");

    var iconClass = valid ? "icon-ok" : "icon-bad";
    var icon = valid ? "\u2713" : "\u2717";
    var durationText = valid ? formatDuration(duration) : "\u2014";

    element.innerHTML =
      '<p class="preview-label">' +
      escapeHtml(label) +
      "</p>" +
      '<p class="preview-name">' +
      '<span class="' +
      iconClass +
      '" aria-hidden="true">' +
      icon +
      "</span>" +
      '<span class="preview-filename">' +
      escapeHtml(file.name) +
      "</span></p>" +
      '<p class="preview-meta">' +
      escapeHtml(formatBytes(file.size)) +
      " &middot; " +
      escapeHtml(durationText) +
      "</p>" +
      (valid
        ? ""
        : '<p class="preview-error">Formato non supportato. Usa WAV, FLAC, AIFF, MP3 o OGG.</p>') +
      '<button type="button" class="remove-button" data-remove="' +
      slot +
      '" aria-label="Rimuovi file ' +
      escapeHtml(file.name) +
      '">Rimuovi</button>';
  }

  /**
   * Render both preview cards and refresh the submit button state.
   *
   * @returns {void}
   */
  function renderPreview() {
    var hasAnyFile = !!(state.userFile || state.referenceFile);
    previewEl.classList.toggle("hidden", !hasAnyFile);
    renderPreviewCard(
      previewUserEl,
      "user",
      state.userFile,
      state.userDuration,
      "La tua traccia"
    );
    renderPreviewCard(
      previewReferenceEl,
      "reference",
      state.referenceFile,
      state.referenceDuration,
      "Reference"
    );
    updateSubmitState();
  }

  /**
   * Store a file in a slot and start reading its duration.
   *
   * @param {"user"|"reference"} slot Slot identifier.
   * @param {File|null} file File to store, or `null` to clear the slot.
   * @returns {void}
   */
  function setFile(slot, file) {
    if (slot === "user") {
      state.userFile = file || null;
      state.userDuration = null;
    } else {
      state.referenceFile = file || null;
      state.referenceDuration = null;
    }

    if (file) {
      readDuration(file).then(function (seconds) {
        // Ignore results for a slot that changed while the metadata was loading.
        if (slot === "user" && state.userFile === file) {
          state.userDuration = seconds;
          renderPreview();
        } else if (slot === "reference" && state.referenceFile === file) {
          state.referenceDuration = seconds;
          renderPreview();
        }
      });
    }

    renderPreview();
  }

  /**
   * Return the first slot that does not hold a file yet.
   *
   * @returns {"user"|"reference"} Slot to fill next.
   */
  function firstFreeSlot() {
    if (!state.userFile) {
      return "user";
    }
    if (!state.referenceFile) {
      return "reference";
    }
    return "user";
  }

  /**
   * Assign dropped or selected files to the preview slots.
   *
   * Two files fill both slots; one file fills the first free slot; anything
   * else is rejected, matching the documented interaction.
   *
   * @param {FileList|File[]} fileList Files chosen by the user.
   * @returns {void}
   */
  function assignFiles(fileList) {
    var files = Array.prototype.slice.call(fileList || []);
    if (files.length === 0) {
      return;
    }
    if (files.length === 1) {
      setFile(firstFreeSlot(), files[0]);
      return;
    }
    if (files.length === 2) {
      setFile("user", files[0]);
      setFile("reference", files[1]);
      return;
    }
    window.alert("Trascina 1 o 2 file");
  }

  /* ------------------------------------------------------------------ *
   * Drag & drop handlers
   * ------------------------------------------------------------------ */

  dropzoneEl.addEventListener("dragover", function (event) {
    event.preventDefault();
    dropzoneEl.classList.add("drag-over");
  });

  dropzoneEl.addEventListener("dragleave", function (event) {
    event.preventDefault();
    dropzoneEl.classList.remove("drag-over");
  });

  dropzoneEl.addEventListener("drop", function (event) {
    event.preventDefault();
    dropzoneEl.classList.remove("drag-over");
    var files = event.dataTransfer && event.dataTransfer.files;
    if (!files || files.length === 0) {
      return;
    }
    if (files.length > 2) {
      window.alert("Trascina 1 o 2 file");
      return;
    }
    assignFiles(files);
  });

  dropzoneEl.addEventListener("click", function (event) {
    // The hidden input is nested in the dropzone: its programmatic click bubbles
    // back here, so ignore it to avoid reopening the picker recursively.
    if (event.target === fileInput) {
      return;
    }
    fileInput.click();
  });

  dropzoneEl.addEventListener("keydown", function (event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", function () {
    assignFiles(fileInput.files);
    // Reset so selecting the same file again still fires a change event.
    fileInput.value = "";
  });

  previewEl.addEventListener("click", function (event) {
    var target = event.target;
    if (!target || typeof target.closest !== "function") {
      return;
    }
    var button = target.closest("[data-remove]");
    if (!button) {
      return;
    }
    setFile(button.getAttribute("data-remove"), null);
  });

  /* ------------------------------------------------------------------ *
   * Submit handling
   * ------------------------------------------------------------------ */

  /**
   * Build the multipart body for `POST /analyze`.
   *
   * @returns {FormData} Body with both files and the selected DAW.
   */
  function buildFormData() {
    var formData = new FormData();
    formData.append("user_file", state.userFile);
    formData.append("reference_file", state.referenceFile);
    formData.append("daw", dawSelect.value);
    return formData;
  }

  /**
   * Handle the form submission: upload both files and render the response.
   *
   * @param {SubmitEvent} event Submit event to intercept.
   * @returns {Promise<void>} Resolves when the request has been fully handled.
   */
  async function handleSubmit(event) {
    event.preventDefault();
    if (state.loading) {
      return;
    }
    if (!isReady()) {
      setStatus("Seleziona due file audio validi prima di analizzare.", true);
      return;
    }

    state.loading = true;
    resultsEl.innerHTML = "";
    setLoadingStatus();
    submitButton.classList.add("loading");
    submitButton.innerHTML =
      '<span class="spinner" aria-hidden="true"></span>Analisi in corso...';
    updateSubmitState();

    var controller = new AbortController();
    var timeoutId = window.setTimeout(function () {
      controller.abort();
    }, REQUEST_TIMEOUT_MS);

    try {
      var response = await fetch("/analyze", {
        method: "POST",
        body: buildFormData(),
        signal: controller.signal,
      });

      if (response.ok) {
        var payload = await response.json();
        renderResults(payload);
        setStatus("Analisi completata.", false);
      } else {
        var detail = "Errore sconosciuto";
        try {
          var errorPayload = await response.json();
          if (errorPayload && errorPayload.detail) {
            detail = Array.isArray(errorPayload.detail)
              ? "Compila tutti i campi richiesti."
              : errorPayload.detail;
          }
        } catch (parseError) {
          detail = "Errore sconosciuto";
        }
        setStatus(String(detail), true);
      }
    } catch (error) {
      if (error && error.name === "AbortError") {
        setStatus("Timeout: il file è troppo grande o il server non risponde", true);
      } else {
        setStatus("Impossibile contattare il server: " + String(error), true);
      }
    } finally {
      window.clearTimeout(timeoutId);
      state.loading = false;
      submitButton.classList.remove("loading");
      submitButton.textContent = "Analizza";
      updateSubmitState();
    }
  }

  /* ------------------------------------------------------------------ *
   * Results rendering
   * ------------------------------------------------------------------ */

  /**
   * Render the "Come procedere" guide from the template embedded in the page.
   *
   * @returns {string} HTML for the guide box.
   */
  function renderGuideBox() {
    var template = document.getElementById("guide-template");
    return template ? template.innerHTML : "";
  }

  /**
   * Pick the CSS class that colours a loudness delta.
   *
   * @param {unknown} delta User minus reference value.
   * @param {number} threshold Absolute delta above which the cell is red.
   * @returns {string} One of `color-ok`, `color-warn`, `color-bad`, or empty.
   */
  function deltaColorClass(delta, threshold) {
    if (typeof delta !== "number" || !isFinite(delta)) {
      return "";
    }
    var magnitude = Math.abs(delta);
    if (magnitude < OK_DELTA_DB) {
      return "color-ok";
    }
    if (magnitude < threshold) {
      return "color-warn";
    }
    return "color-bad";
  }

  /**
   * Build one loudness table row.
   *
   * @param {string} label Row label.
   * @param {number} user Value measured on the user track.
   * @param {number} reference Value measured on the reference track.
   * @param {number} delta User minus reference.
   * @param {number} threshold Absolute delta above which the row is flagged.
   * @param {number} digits Number of decimals to show.
   * @returns {string} HTML for the row.
   */
  function loudnessRow(label, user, reference, delta, threshold, digits) {
    var colorClass = deltaColorClass(delta, threshold);
    var deltaClass = "numeric" + (colorClass ? " " + colorClass : "");
    return (
      '<tr><th scope="row">' +
      escapeHtml(label) +
      '</th><td class="numeric">' +
      formatNumber(user, digits) +
      '</td><td class="numeric">' +
      formatNumber(reference, digits) +
      "</td><td class=\"" +
      deltaClass +
      '">' +
      formatNumber(delta, digits) +
      "</td></tr>"
    );
  }

  /**
   * Render the loudness summary section with colour-coded deltas.
   *
   * @param {object} report Comparison report from the API.
   * @returns {string} HTML for the section.
   */
  function renderLoudnessSection(report) {
    var user = report.user_loudness || {};
    var reference = report.reference_loudness || {};
    var delta = report.loudness_delta || {};
    var rows = [
      loudnessRow(
        "Integrated LUFS",
        user.integrated_lufs,
        reference.integrated_lufs,
        delta.integrated_lufs_delta,
        LUFS_DELTA_THRESHOLD_DB,
        1
      ),
      loudnessRow(
        "True Peak (dBTP)",
        user.true_peak_dbtp,
        reference.true_peak_dbtp,
        delta.true_peak_dbtp_delta,
        TRUE_PEAK_DELTA_THRESHOLD_DB,
        1
      ),
      loudnessRow(
        "Loudness Range (LU)",
        user.loudness_range_lu,
        reference.loudness_range_lu,
        delta.loudness_range_lu_delta,
        LRA_DELTA_THRESHOLD_DB,
        1
      ),
    ];

    return (
      "<section><h3>Sintesi loudness</h3>" +
      '<div class="table-scroll"><table>' +
      '<thead><tr><th scope="col">Metrica</th><th scope="col">User</th>' +
      '<th scope="col">Reference</th><th scope="col">Delta</th></tr></thead>' +
      "<tbody>" +
      rows.join("") +
      "</tbody></table></div></section>"
    );
  }

  /**
   * Find the index of the band whose center frequency is closest to a target.
   *
   * @param {object[]} bands Band objects carrying `freq_hz`.
   * @param {number} freq Target frequency in Hz.
   * @returns {number} Index of the nearest band.
   */
  function nearestBandIndex(bands, freq) {
    var best = 0;
    var bestDistance = Infinity;
    bands.forEach(function (band, index) {
      var distance = Math.abs(band.freq_hz - freq);
      if (distance < bestDistance) {
        best = index;
        bestDistance = distance;
      }
    });
    return best;
  }

  /**
   * Format an X-axis frequency tick.
   *
   * @param {number} freq Frequency in Hz.
   * @returns {string} `100`, `1k`, or `10k`.
   */
  function formatFrequencyTick(freq) {
    return freq >= 1000 ? freq / 1000 + "k" : String(freq);
  }

  /**
   * Serialise the spectrum comparison as an inline SVG chart.
   *
   * No chart library is used: the polyline coordinates are computed by hand on
   * the `0 0 700 300` viewBox, and the CSS scales the SVG to its container.
   *
   * @param {object} report Comparison report from the API.
   * @returns {string} SVG markup, or a fallback paragraph without band data.
   */
  function drawSpectrumChart(report) {
    var bands = (report.spectrum && report.spectrum.bands) || [];
    if (bands.length === 0) {
      return '<p class="empty">Dati spettrali non disponibili.</p>';
    }

    var rawMin = Infinity;
    var rawMax = -Infinity;
    bands.forEach(function (band) {
      [band.user_db, band.reference_db].forEach(function (value) {
        if (typeof value === "number" && isFinite(value)) {
          if (value < rawMin) {
            rawMin = value;
          }
          if (value > rawMax) {
            rawMax = value;
          }
        }
      });
    });
    if (!isFinite(rawMin) || !isFinite(rawMax)) {
      return '<p class="empty">Dati spettrali non disponibili.</p>';
    }

    // Clamp the floor at -60 dB: a full -120 dB axis would be unreadable.
    var low = Math.max(CHART_FLOOR_DB, rawMin - 5);
    var high = Math.max(rawMax + 5, low + 10);

    var plotWidth = CHART_WIDTH - CHART_PAD_LEFT - CHART_PAD_RIGHT;
    var plotHeight = CHART_HEIGHT - CHART_PAD_TOP - CHART_PAD_BOTTOM;
    var axisBottom = CHART_HEIGHT - CHART_PAD_BOTTOM;

    function xFor(index) {
      if (bands.length === 1) {
        return CHART_PAD_LEFT + plotWidth / 2;
      }
      return CHART_PAD_LEFT + (index / (bands.length - 1)) * plotWidth;
    }

    function yFor(value) {
      var clamped = Math.max(low, Math.min(high, value));
      return CHART_PAD_TOP + ((high - clamped) / (high - low)) * plotHeight;
    }

    function pointsFor(key) {
      return bands
        .map(function (band, index) {
          return xFor(index).toFixed(1) + "," + yFor(band[key]).toFixed(1);
        })
        .join(" ");
    }

    var parts = [];
    parts.push(
      '<svg viewBox="0 0 ' +
        CHART_WIDTH +
        " " +
        CHART_HEIGHT +
        '" class="spectrum-chart" role="img" ' +
        'preserveAspectRatio="xMidYMid meet" ' +
        'aria-label="Confronto dello spettro tra la tua traccia e il riferimento">'
    );

    // Legend, top left.
    parts.push(
      '<text x="' +
        CHART_PAD_LEFT +
        '" y="20" font-size="13" fill="' +
        CHART_USER_COLOR +
        '">\u2014 La tua traccia</text>'
    );
    parts.push(
      '<text x="' +
        (CHART_PAD_LEFT + 140) +
        '" y="20" font-size="13" fill="' +
        CHART_REFERENCE_COLOR +
        '">-- Reference</text>'
    );

    // Horizontal grid lines and Y ticks (min, mid, max).
    [low, (low + high) / 2, high].forEach(function (value) {
      var y = yFor(value).toFixed(1);
      parts.push(
        '<line x1="' +
          CHART_PAD_LEFT +
          '" y1="' +
          y +
          '" x2="' +
          (CHART_WIDTH - CHART_PAD_RIGHT) +
          '" y2="' +
          y +
          '" stroke="#e5e7eb" stroke-width="1" />'
      );
      parts.push(
        '<text x="' +
          (CHART_PAD_LEFT - 8) +
          '" y="' +
          y +
          '" font-size="11" fill="#6b7280" text-anchor="end" ' +
          'dominant-baseline="middle">' +
          escapeHtml(formatNumber(value, 0)) +
          " dB</text>"
      );
    });

    // Vertical grid lines and X ticks at 100 Hz, 1 kHz, and 10 kHz.
    [100, 1000, 10000].forEach(function (freq) {
      var x = xFor(nearestBandIndex(bands, freq)).toFixed(1);
      parts.push(
        '<line x1="' +
          x +
          '" y1="' +
          CHART_PAD_TOP +
          '" x2="' +
          x +
          '" y2="' +
          axisBottom +
          '" stroke="#f3f4f6" stroke-width="1" />'
      );
      parts.push(
        '<text x="' +
          x +
          '" y="' +
          (axisBottom + 18) +
          '" font-size="11" fill="#6b7280" text-anchor="middle">' +
          escapeHtml(formatFrequencyTick(freq)) +
          "</text>"
      );
    });

    // Axes.
    parts.push(
      '<line x1="' +
        CHART_PAD_LEFT +
        '" y1="' +
        axisBottom +
        '" x2="' +
        (CHART_WIDTH - CHART_PAD_RIGHT) +
        '" y2="' +
        axisBottom +
        '" stroke="#9ca3af" stroke-width="1" />'
    );
    parts.push(
      '<line x1="' +
        CHART_PAD_LEFT +
        '" y1="' +
        CHART_PAD_TOP +
        '" x2="' +
        CHART_PAD_LEFT +
        '" y2="' +
        axisBottom +
        '" stroke="#9ca3af" stroke-width="1" />'
    );

    // Reference first so the user line stays on top.
    parts.push(
      '<polyline fill="none" stroke="' +
        CHART_REFERENCE_COLOR +
        '" stroke-width="2" stroke-dasharray="4 2" points="' +
        pointsFor("reference_db") +
        '" />'
    );
    parts.push(
      '<polyline fill="none" stroke="' +
        CHART_USER_COLOR +
        '" stroke-width="2" points="' +
        pointsFor("user_db") +
        '" />'
    );

    parts.push("</svg>");
    return parts.join("");
  }

  /**
   * Render the spectral imbalance section: chart plus only non-ok bands.
   *
   * @param {object} report Comparison report from the API.
   * @returns {string} HTML for the section.
   */
  function renderSpectrumSection(report) {
    var bands = (report.spectrum && report.spectrum.bands) || [];
    var problems = bands.filter(function (band) {
      return band.severity !== "ok";
    });

    var body;
    if (problems.length === 0) {
      body = '<p class="empty">Nessuno squilibrio tonale rilevato.</p>';
    } else {
      body =
        '<div class="table-scroll"><table><thead><tr>' +
        '<th scope="col">Banda (Hz)</th><th scope="col">User (dB)</th>' +
        '<th scope="col">Reference (dB)</th><th scope="col">Delta (dB)</th>' +
        '<th scope="col">Severity</th></tr></thead><tbody>' +
        problems
          .map(function (band) {
            var colorClass = band.severity === "major" ? "color-bad" : "color-warn";
            return (
              '<tr><td class="numeric">' +
              formatNumber(band.freq_hz, 0) +
              '</td><td class="numeric">' +
              formatNumber(band.user_db, 1) +
              '</td><td class="numeric">' +
              formatNumber(band.reference_db, 1) +
              '</td><td class="numeric ' +
              colorClass +
              '">' +
              formatNumber(band.delta_db, 1) +
              "</td><td>" +
              escapeHtml(band.severity) +
              "</td></tr>"
            );
          })
          .join("") +
        "</tbody></table></div>";
    }

    return (
      '<section><h3>Spettro</h3><div class="chart-container">' +
      drawSpectrumChart(report) +
      "</div>" +
      body +
      "</section>"
    );
  }

  /**
   * Render the stereo section, or the mono fallback message.
   *
   * @param {object} report Comparison report from the API.
   * @returns {string} HTML for the section.
   */
  function renderStereoSection(report) {
    var stereo = report.stereo;
    if (!stereo) {
      return (
        "<section><h3>Stereo</h3>" +
        '<p class="empty">Analisi stereo non disponibile (file mono).</p></section>'
      );
    }

    return (
      '<section><h3>Stereo</h3><div class="table-scroll"><table><thead><tr>' +
      '<th scope="col">Metrica</th><th scope="col">Delta</th></tr></thead><tbody>' +
      '<tr><th scope="row">Correlation media</th><td class="numeric">' +
      formatNumber(stereo.overall_correlation_delta, 2) +
      "</td></tr>" +
      '<tr><th scope="row">Side/Mid medio (dB)</th><td class="numeric">' +
      formatNumber(stereo.overall_side_to_mid_delta_db, 1) +
      "</td></tr>" +
      "</tbody></table></div></section>"
    );
  }

  /**
   * Render one suggestion as a structured card.
   *
   * @param {object} suggestion Structured suggestion from the API.
   * @param {string} rendered DAW-ready text for the same suggestion.
   * @returns {string} HTML for the card.
   */
  function renderSuggestionCard(suggestion, rendered) {
    var severity = suggestion.severity || "info";
    return (
      '<article class="suggestion-card">' +
      '<span class="badge-large ' +
      escapeHtml(severity) +
      '">P' +
      escapeHtml(suggestion.priority) +
      "</span>" +
      '<div class="suggestion-content">' +
      "<h4>" +
      escapeHtml(suggestion.title) +
      "</h4>" +
      '<p class="action"><span class="action-label">In Ableton:</span>' +
      escapeHtml(rendered || "") +
      "</p>" +
      '<p class="why">' +
      escapeHtml(suggestion.explanation) +
      "</p></div></article>"
    );
  }

  /**
   * Render the DAW-agnostic suggestions section, ordered by priority.
   *
   * @param {object} payload Full API response.
   * @returns {string} HTML for the section.
   */
  function renderSuggestionsSection(payload) {
    var suggestions = payload.suggestions || [];
    var rendered = payload.rendered_suggestions || [];

    var ordered = suggestions
      .map(function (suggestion, index) {
        return { suggestion: suggestion, rendered: rendered[index] };
      })
      .sort(function (a, b) {
        return (a.suggestion.priority || 0) - (b.suggestion.priority || 0);
      });

    var cards = ordered
      .map(function (entry) {
        return renderSuggestionCard(entry.suggestion, entry.rendered);
      })
      .join("");

    return '<section><h3>Suggerimenti</h3><div class="suggestion-list">' + cards + "</div></section>";
  }

  /**
   * Render the positive empty state used when there is nothing to fix.
   *
   * @returns {string} HTML for the success box.
   */
  function renderEmptyState() {
    return (
      '<section class="success" role="status">' +
      '<div class="success-icon" aria-hidden="true">\u2713</div>' +
      "<h3>Ottimo lavoro!</h3>" +
      "<p>La traccia è già vicina al riferimento. Nessun intervento necessario.</p>" +
      "</section>"
    );
  }

  /**
   * Render the warnings section, or an empty string when there is nothing to say.
   *
   * @param {object} report Comparison report from the API.
   * @returns {string} HTML for the section.
   */
  function renderWarningsSection(report) {
    var warnings = report.warnings || [];
    if (warnings.length === 0) {
      return "";
    }

    var items = warnings
      .map(function (warning) {
        return "<li>" + escapeHtml(warning) + "</li>";
      })
      .join("");

    return '<section><h3>Warning</h3><ul class="warnings">' + items + "</ul></section>";
  }

  /**
   * Render the whole analysis payload into `#results`.
   *
   * @param {object} payload JSON returned by `POST /analyze`.
   * @returns {void}
   */
  function renderResults(payload) {
    var report = payload.report || {};
    var hasSuggestions = (payload.suggestions || []).length > 0;
    var parts = [];

    if (hasSuggestions) {
      parts.push(renderGuideBox());
    }
    parts.push(renderLoudnessSection(report));
    parts.push(renderSpectrumSection(report));
    parts.push(renderStereoSection(report));
    parts.push(
      hasSuggestions ? renderSuggestionsSection(payload) : renderEmptyState()
    );
    parts.push(renderWarningsSection(report));

    resultsEl.innerHTML = parts.join("");
  }

  /* ------------------------------------------------------------------ *
   * Bootstrap
   * ------------------------------------------------------------------ */

  analyzeForm.addEventListener("submit", handleSubmit);
  renderPreview();
})();
