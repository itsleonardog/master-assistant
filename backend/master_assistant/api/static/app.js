/**
 * Master Assistant UI controller.
 *
 * The page is served as plain static files, so no bundler and no framework is
 * involved: this file reads the two file inputs, POSTs them to `/analyze`, and
 * renders the JSON payload into the `#results` container.
 *
 * NOTE: this file is intentionally dependency-free and is not covered by
 * automated tests; exercise it manually in a browser.
 */

(function () {
  "use strict";

  /** Threshold in dB above which a loudness delta is flagged as problematic. */
  var LUFS_DELTA_THRESHOLD_DB = 2.0;
  /** Threshold in dB above which a true-peak delta is flagged as problematic. */
  var TRUE_PEAK_DELTA_THRESHOLD_DB = 1.0;

  var analyzeForm = document.getElementById("analyze-form");
  var referenceForm = document.getElementById("reference-form");
  var statusEl = document.getElementById("status");
  var resultsEl = document.getElementById("results");
  var submitButton = document.getElementById("submit-button");

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
    var isOutOfRange = typeof delta === "number" && Math.abs(delta) > threshold;
    var deltaClass = isOutOfRange ? ' class="numeric delta-bad"' : ' class="numeric"';
    return (
      "<tr><th scope=\"row\">" +
      escapeHtml(label) +
      "</th><td class=\"numeric\">" +
      formatNumber(user, digits) +
      "</td><td class=\"numeric\">" +
      formatNumber(reference, digits) +
      "</td><td" +
      deltaClass +
      ">" +
      formatNumber(delta, digits) +
      "</td></tr>"
    );
  }

  /**
   * Render the loudness summary section.
   *
   * @param {object} report Comparison report from the API.
   * @returns {string} HTML for the section.
   */
  function renderLoudnessSection(report) {
    var user = report.user_loudness;
    var reference = report.reference_loudness;
    var delta = report.loudness_delta;
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
        LUFS_DELTA_THRESHOLD_DB,
        1
      ),
    ];

    return (
      "<section><h3>Sintesi loudness</h3><table>" +
      "<thead><tr><th scope=\"col\">Metrica</th><th scope=\"col\">User</th>" +
      "<th scope=\"col\">Reference</th><th scope=\"col\">Delta</th></tr></thead>" +
      "<tbody>" +
      rows.join("") +
      "</tbody></table></section>"
    );
  }

  /**
   * Render the spectral imbalance section, showing only non-ok bands.
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
        "<table><thead><tr>" +
        '<th scope="col">Banda (Hz)</th><th scope="col">User (dB)</th>' +
        '<th scope="col">Reference (dB)</th><th scope="col">Delta (dB)</th>' +
        '<th scope="col">Severity</th></tr></thead><tbody>' +
        problems
          .map(function (band) {
            var deltaClass =
              band.severity === "major" ? ' class="numeric delta-bad"' : ' class="numeric"';
            return (
              "<tr><td class=\"numeric\">" +
              formatNumber(band.freq_hz, 0) +
              "</td><td class=\"numeric\">" +
              formatNumber(band.user_db, 1) +
              "</td><td class=\"numeric\">" +
              formatNumber(band.reference_db, 1) +
              "</td><td" +
              deltaClass +
              ">" +
              formatNumber(band.delta_db, 1) +
              "</td><td>" +
              escapeHtml(band.severity) +
              "</td></tr>"
            );
          })
          .join("") +
        "</tbody></table>";
    }

    return "<section><h3>Spettro</h3>" + body + "</section>";
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
      "<section><h3>Stereo</h3><table><thead><tr>" +
      '<th scope="col">Metrica</th><th scope="col">Delta</th></tr></thead><tbody>' +
      '<tr><th scope="row">Correlation media</th><td class="numeric">' +
      formatNumber(stereo.overall_correlation_delta, 2) +
      "</td></tr>" +
      '<tr><th scope="row">Side/Mid medio (dB)</th><td class="numeric">' +
      formatNumber(stereo.overall_side_to_mid_delta_db, 1) +
      "</td></tr>" +
      "</tbody></table></section>"
    );
  }

  /**
   * Render one suggestion item with its priority badge and rendered text.
   *
   * @param {object} suggestion Structured suggestion from the API.
   * @param {string} rendered DAW-ready text for the same suggestion.
   * @returns {string} HTML for the list item.
   */
  function renderSuggestion(suggestion, rendered) {
    var severity = suggestion.severity || "info";
    return (
      '<li class="suggestion">' +
      '<span class="badge ' +
      escapeHtml(severity) +
      '">P' +
      escapeHtml(suggestion.priority) +
      "</span>" +
      '<div class="suggestion-body">' +
      '<p class="suggestion-title">' +
      escapeHtml(suggestion.title) +
      "</p>" +
      '<p class="suggestion-explanation">' +
      escapeHtml(suggestion.explanation) +
      "</p>" +
      "<code>" +
      escapeHtml(rendered || "") +
      "</code>" +
      "</div></li>"
    );
  }

  /**
   * Render the DAW-agnostic suggestions section.
   *
   * @param {object} payload Full API response.
   * @returns {string} HTML for the section.
   */
  function renderSuggestionsSection(payload) {
    var suggestions = payload.suggestions || [];
    var rendered = payload.rendered_suggestions || [];

    if (suggestions.length === 0) {
      return (
        "<section><h3>Suggerimenti</h3>" +
        '<p class="empty">Nessun suggerimento: la traccia è già vicina al riferimento.</p>' +
        "</section>"
      );
    }

    var ordered = suggestions
      .map(function (suggestion, index) {
        return { suggestion: suggestion, rendered: rendered[index] };
      })
      .sort(function (a, b) {
        return (a.suggestion.priority || 0) - (b.suggestion.priority || 0);
      });

    var items = ordered
      .map(function (entry) {
        return renderSuggestion(entry.suggestion, entry.rendered);
      })
      .join("");

    return '<section><h3>Suggerimenti</h3><ol class="suggestions">' + items + "</ol></section>";
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
    resultsEl.innerHTML = [
      renderLoudnessSection(report),
      renderSpectrumSection(report),
      renderStereoSection(report),
      renderSuggestionsSection(payload),
      renderWarningsSection(report),
    ].join("");
  }

  /**
   * Build the multipart body from both forms.
   *
   * The two file inputs live in separate `<form>` elements, so the body is
   * assembled by hand instead of relying on the browser form serialization.
   *
   * @returns {FormData} Body ready for `POST /analyze`.
   */
  function buildFormData() {
    var userFile = document.getElementById("user_file").files[0];
    var referenceFile = document.getElementById("reference_file").files[0];
    var daw = document.getElementById("daw").value;
    var formData = new FormData();

    if (userFile) {
      formData.append("user_file", userFile);
    }
    if (referenceFile) {
      formData.append("reference_file", referenceFile);
    }
    formData.append("daw", daw);
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
    submitButton.disabled = true;
    setStatus("Analisi in corso...", false);
    resultsEl.innerHTML = "";

    try {
      var response = await fetch("/analyze", {
        method: "POST",
        body: buildFormData(),
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
            if (Array.isArray(errorPayload.detail)) {
              // FastAPI validation errors: 422
              detail = "Compila tutti i campi richiesti.";
            } else {
              detail = errorPayload.detail;
            }
          }
        } catch (parseError) {
          detail = "Errore sconosciuto";
        }
        setStatus(String(detail), true);
      }
    } catch (networkError) {
      setStatus("Impossibile contattare il server: " + String(networkError), true);
    } finally {
      submitButton.disabled = false;
    }
  }

  analyzeForm.addEventListener("submit", handleSubmit);
  // The reference fields sit in their own form; submitting it runs the same flow.
  referenceForm.addEventListener("submit", handleSubmit);
})();
