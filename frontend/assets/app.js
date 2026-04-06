const AUTH_STORAGE_KEY = "virtualChoirAuth";
const API_BASE_URL = "https://virtualchoir.onrender.com"; // Update this with your Render backend URL

const byId = (id) => document.getElementById(id);

const setStatus = (element, message, isError = false) => {
  if (!element) {
    return;
  }

  element.textContent = message;
  element.classList.toggle("error", isError);
};

const formatDate = (iso) => {
  const date = new Date(iso);
  return Number.isNaN(date.valueOf()) ? iso : date.toLocaleString();
};

const formatCurrency = (amount, currency = "KES") => {
  if (typeof amount !== "number") {
    return "";
  }

  try {
    return new Intl.NumberFormat("en-KE", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${currency} ${amount}`;
  }
};

const safeJson = async (response) => {
  try {
    return await response.json();
  } catch {
    return {};
  }
};

const renderWarnings = (listElement, warnings) => {
  if (!listElement) {
    return;
  }

  listElement.innerHTML = "";
  if (!warnings.length) {
    listElement.hidden = true;
    return;
  }

  listElement.hidden = false;
  warnings.forEach((warning) => {
    const item = document.createElement("li");
    item.textContent = warning;
    listElement.appendChild(item);
  });
};

const getStoredAuth = () => {
  try {
    return JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY) || "null");
  } catch {
    return null;
  }
};

const setStoredAuth = (payload) => {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(payload));
};

const clearStoredAuth = () => {
  localStorage.removeItem(AUTH_STORAGE_KEY);
};

const getAccessToken = () => getStoredAuth()?.session?.access_token || null;

const authorizedFetch = (url, options = {}) => {
  const headers = new Headers(options.headers || {});
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const fullUrl = url.startsWith('http') ? url : API_BASE_URL + url;
  return fetch(fullUrl, { ...options, headers });
};

const loadCurrentUser = async () => {
  const token = getAccessToken();
  if (!token) {
    return null;
  }

  const response = await authorizedFetch("/auth/me");
  const payload = await safeJson(response);
  if (!response.ok) {
    if (response.status === 401) {
      clearStoredAuth();
      return null;
    }
    throw new Error(payload.detail || "Could not load the current account.");
  }

  const auth = getStoredAuth() || {};
  auth.user = payload;
  setStoredAuth(auth);
  return payload;
};

const renderCardList = (container, items, renderItem) => {
  if (!container) {
    return;
  }

  container.innerHTML = "";
  items.forEach((item) => container.appendChild(renderItem(item)));
};

const initPracticePage = () => {
  const form = byId("score-form");
  if (!form) {
    return;
  }

  const fileInput = byId("score-file");
  const submitButton = byId("score-submit");
  const status = byId("score-status");
  const result = byId("score-result");
  const empty = byId("score-empty");
  const sourceBadge = byId("score-source");
  const audio = byId("practice-audio");
  const sourceFilePath = byId("source-file-path");
  const parseFilePath = byId("parse-file-path");
  const convertedRow = byId("converted-row");
  const convertedFilePath = byId("converted-file-path");
  const midiFilePath = byId("midi-file-path");
  const wavFilePath = byId("wav-file-path");
  const scoreSummary = byId("score-summary");
  const warnings = byId("score-warnings");
  const noteCount = byId("stat-note-count");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const file = fileInput?.files?.[0];
    if (!file) {
      setStatus(status, "Please choose a score file first.", true);
      return;
    }

    submitButton.disabled = true;
    setStatus(status, "Uploading score, preparing notation, and rendering audio...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(API_BASE_URL + "/upload-score", {
        method: "POST",
        body: formData,
      });
      const payload = await safeJson(response);

      if (!response.ok) {
        throw new Error(payload.detail || "Score upload failed.");
      }

      const partCount = payload.parsed_score.parts.length;
      const notes = payload.parsed_score.parts.reduce(
        (total, part) => total + part.notes.filter((note) => !note.is_rest).length,
        0,
      );

      sourceBadge.textContent = payload.source_type === "pdf" ? "PDF score via Audiveris" : "Direct MusicXML score";
      audio.src = `${payload.audio_url}?t=${Date.now()}`;
      sourceFilePath.textContent = payload.source_file_path;
      parseFilePath.textContent = payload.parse_file_path;
      midiFilePath.textContent = payload.midi_file_path;
      wavFilePath.textContent = payload.wav_file_path;
      scoreSummary.textContent = `Rendered ${notes} note events across ${partCount} part${partCount === 1 ? "" : "s"} at ${payload.parsed_score.tempo_bpm} BPM.`;
      if (noteCount) {
        noteCount.textContent = `${notes} notes`;
      }

      if (payload.converted_musicxml_path) {
        convertedRow.hidden = false;
        convertedFilePath.textContent = payload.converted_musicxml_path;
      } else {
        convertedRow.hidden = true;
        convertedFilePath.textContent = "";
      }

      renderWarnings(warnings, payload.warnings || []);
      result.hidden = false;
      empty.hidden = true;
      setStatus(status, "Practice audio generated successfully.");
    } catch (error) {
      setStatus(status, error.message || "Something went wrong while processing the score.", true);
    } finally {
      submitButton.disabled = false;
    }
  });

  renderWarnings(warnings, []);
};

const initStudioPage = () => {
  const form = byId("voice-form");
  const takesList = byId("takes-list");
  const takesEmpty = byId("takes-empty");
  const takesFilter = byId("takes-filter");
  const takeCount = byId("stat-take-count");
  const voiceStatus = byId("voice-status");
  const voicePreview = byId("voice-preview");
  const voiceFileInput = byId("voice-file");
  const recordButton = byId("record-button");
  const stopButton = byId("stop-button");
  const submitButton = byId("voice-submit");

  if (!form || !takesList || !takesEmpty || !takesFilter) {
    return;
  }

  const singerNameInput = byId("singer-name");
  const voicePartInput = byId("voice-part");
  const takeLabelInput = byId("take-label");
  const voiceNotesInput = byId("voice-notes");

  let mediaRecorder = null;
  let mediaStream = null;
  let recordedChunks = [];
  let recordedBlob = null;
  let takesCache = [];

  const renderTakes = (filterValue = "") => {
    const query = filterValue.trim().toLowerCase();
    const visible = query
      ? takesCache.filter((take) =>
          [take.singer_name, take.voice_part, take.take_label || "", take.notes || ""].some((value) =>
            value.toLowerCase().includes(query),
          ),
        )
      : takesCache;

    takesList.innerHTML = "";
    if (takeCount) {
      takeCount.textContent = `${takesCache.length} take${takesCache.length === 1 ? "" : "s"}`;
    }
    takesEmpty.hidden = visible.length > 0;
    takesEmpty.textContent = query ? "No takes match your filter." : "No voice takes uploaded yet.";

    visible.forEach((take) => {
      const card = document.createElement("article");
      card.className = "take-card";
      card.innerHTML = `
        <div class="take-top">
          <div>
            <h3>${take.singer_name} - ${take.voice_part}</h3>
            <div class="take-meta">${take.take_label || "Untitled take"}</div>
          </div>
          <div class="take-meta">${formatDate(take.uploaded_at)}</div>
        </div>
        <audio controls preload="metadata" src="${take.audio_url}"></audio>
        <div class="take-meta">Stored file: <code>${take.stored_file_path}</code></div>
        <div class="take-meta">${take.notes || "No notes provided."}</div>
      `;
      takesList.appendChild(card);
    });
  };

  const loadTakes = async () => {
    try {
      const response = await fetch(API_BASE_URL + "/voice-takes");
      const takes = await safeJson(response);
      if (!response.ok) {
        throw new Error("Could not load voice takes.");
      }

      takesCache = Array.isArray(takes) ? takes : [];
      renderTakes(takesFilter.value);
    } catch (error) {
      takesCache = [];
      takesList.innerHTML = "";
      if (takeCount) {
        takeCount.textContent = "0 takes";
      }
      takesEmpty.hidden = false;
      takesEmpty.textContent = error.message || "Could not load voice takes.";
    }
  };

  const resetRecordedPreview = () => {
    recordedBlob = null;
    if (!voiceFileInput.files?.length) {
      voicePreview.hidden = true;
      voicePreview.removeAttribute("src");
    }
  };

  voiceFileInput.addEventListener("change", () => {
    if (voiceFileInput.files?.[0]) {
      recordedBlob = null;
      voicePreview.src = URL.createObjectURL(voiceFileInput.files[0]);
      voicePreview.hidden = false;
      setStatus(voiceStatus, "Audio file selected and ready to upload.");
    } else {
      resetRecordedPreview();
    }
  });

  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    recordButton.disabled = true;
    stopButton.disabled = true;
    setStatus(voiceStatus, "Browser recording is not available here. You can still upload an audio file.");
  }

  recordButton.addEventListener("click", async () => {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordedChunks = [];
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      mediaRecorder = new MediaRecorder(mediaStream, { mimeType });
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.push(event.data);
        }
      };
      mediaRecorder.onstop = () => {
        recordedBlob = new Blob(recordedChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        voicePreview.src = URL.createObjectURL(recordedBlob);
        voicePreview.hidden = false;
        setStatus(voiceStatus, "Recording captured and ready to upload.");
        mediaStream?.getTracks().forEach((track) => track.stop());
        mediaStream = null;
      };
      mediaRecorder.start();
      recordButton.disabled = true;
      stopButton.disabled = false;
      setStatus(voiceStatus, "Recording in progress...");
    } catch (error) {
      setStatus(voiceStatus, error.message || "Microphone access failed.", true);
    }
  });

  stopButton.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    recordButton.disabled = false;
    stopButton.disabled = true;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const singerName = singerNameInput.value.trim();
    const voicePart = voicePartInput.value.trim();
    const takeLabel = takeLabelInput.value.trim();
    const notes = voiceNotesInput.value.trim();
    const fileFromPicker = voiceFileInput.files?.[0] || null;

    if (!singerName) {
      setStatus(voiceStatus, "Singer name is required.", true);
      return;
    }
    if (!voicePart) {
      setStatus(voiceStatus, "Voice part is required.", true);
      return;
    }
    if (!fileFromPicker && !recordedBlob) {
      setStatus(voiceStatus, "Choose an audio file or record a take first.", true);
      return;
    }

    submitButton.disabled = true;
    setStatus(voiceStatus, "Uploading voice take...");

    const formData = new FormData();
    formData.append("singer_name", singerName);
    formData.append("voice_part", voicePart);
    if (takeLabel) {
      formData.append("take_label", takeLabel);
    }
    if (notes) {
      formData.append("notes", notes);
    }
    if (fileFromPicker) {
      formData.append("file", fileFromPicker);
    } else if (recordedBlob) {
      formData.append("file", recordedBlob, `${voicePart.toLowerCase()}-${singerName.toLowerCase().replace(/\s+/g, "-")}.webm`);
    }

    try {
      const response = await fetch(API_BASE_URL + "/upload-voice", {
        method: "POST",
        body: formData,
      });
      const payload = await safeJson(response);
      if (!response.ok) {
        throw new Error(payload.detail || "Voice upload failed.");
      }

      setStatus(voiceStatus, `Voice take uploaded for ${payload.singer_name}.`);
      form.reset();
      voicePreview.hidden = true;
      voicePreview.removeAttribute("src");
      recordedBlob = null;
      await loadTakes();
    } catch (error) {
      setStatus(voiceStatus, error.message || "Something went wrong while uploading the voice take.", true);
    } finally {
      submitButton.disabled = false;
      recordButton.disabled = !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined";
      stopButton.disabled = true;
    }
  });

  takesFilter.addEventListener("input", () => renderTakes(takesFilter.value));
  loadTakes();
};

const initPilotPage = () => {
  const form = byId("pilot-form");
  const status = byId("pilot-status");
  if (!form || !status) {
    return;
  }

  const nameInput = byId("pilot-name");
  const emailInput = byId("pilot-email");
  const organizationInput = byId("pilot-organization");
  const typeInput = byId("pilot-type");
  const sizeInput = byId("pilot-size");
  const notesInput = byId("pilot-notes");
  const submitButton = byId("pilot-submit");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const payload = {
      contact_name: nameInput.value.trim(),
      email: emailInput.value.trim(),
      organization: organizationInput.value.trim(),
      choir_type: typeInput.value.trim() || null,
      choir_size: sizeInput.value.trim() || null,
      notes: notesInput.value.trim() || null,
    };

    if (!payload.contact_name) {
      setStatus(status, "Contact name is required.", true);
      return;
    }
    if (!payload.email) {
      setStatus(status, "Email is required.", true);
      return;
    }
    if (!payload.organization) {
      setStatus(status, "Choir or organization name is required.", true);
      return;
    }

    submitButton.disabled = true;
    setStatus(status, "Saving pilot request...");

    try {
      const response = await fetch(API_BASE_URL + "/pilot-interest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const lead = await safeJson(response);
      if (!response.ok) {
        throw new Error(lead.detail || "Pilot request failed.");
      }

      form.reset();
      setStatus(status, `Pilot request saved for ${lead.organization}. We can now follow up through the admin desk.`);
    } catch (error) {
      setStatus(status, error.message || "Something went wrong while saving the pilot request.", true);
    } finally {
      submitButton.disabled = false;
    }
  });
};

const renderAccount = (user) => {
  const roleBadge = byId("auth-role-badge");
  const sessionEmpty = byId("auth-session-empty");
  const sessionCard = byId("auth-session-card");
  const userName = byId("auth-user-name");
  const userEmail = byId("auth-user-email");
  const userRole = byId("auth-user-role");
  const userSubscription = byId("auth-user-subscription");
  const refreshPaymentButton = byId("refresh-payment-button");

  if (!roleBadge || !sessionEmpty || !sessionCard) {
    return;
  }

  if (!user) {
    roleBadge.textContent = "Logged out";
    roleBadge.classList.remove("alt");
    sessionEmpty.hidden = false;
    sessionCard.hidden = true;
    if (refreshPaymentButton) {
      refreshPaymentButton.disabled = true;
    }
    return;
  }

  roleBadge.textContent = user.role === "admin" ? "Admin account" : "User account";
  if (user.role === "admin") {
    roleBadge.classList.add("alt");
  } else {
    roleBadge.classList.remove("alt");
  }

  sessionEmpty.hidden = true;
  sessionCard.hidden = false;
  userName.textContent = user.full_name || "Not provided";
  userEmail.textContent = user.email || "Unknown";
  userRole.textContent = user.role;
  userSubscription.textContent = user.subscription?.status
    ? [
        user.subscription.status,
        user.subscription.plan_name ? `plan ${user.subscription.plan_name}` : "",
        typeof user.subscription.amount === "number"
          ? formatCurrency(user.subscription.amount, user.subscription.currency || "KES")
          : "",
      ]
        .filter(Boolean)
        .join(" · ")
    : "No payment yet";

  if (refreshPaymentButton) {
    refreshPaymentButton.disabled = !(
      user.subscription?.payhero_reference || user.subscription?.payhero_external_reference
    );
  }
};

const renderBillingPlans = async (user) => {
  const container = byId("billing-plans");
  const empty = byId("billing-empty");
  const phoneInput = byId("payment-phone");
  if (!container || !empty) {
    return;
  }

  try {
    const response = await fetch(API_BASE_URL + "/billing/plans");
    const plans = await safeJson(response);
    if (!response.ok) {
      throw new Error("Could not load billing plans.");
    }

    const availablePlans = Array.isArray(plans) ? plans : [];
    empty.hidden = availablePlans.length > 0;
    container.innerHTML = "";

    availablePlans.forEach((plan) => {
      const card = document.createElement("article");
      card.className = "card";
      const buttonLabel = !plan.available
        ? "PayHero not configured"
        : user
          ? `Send ${plan.label} prompt`
          : "Sign in to pay";
      card.innerHTML = `
        <h3>${plan.label}</h3>
        <p class="copy">${plan.description}</p>
        <p class="stat-value" style="font-size:1.5rem; margin-top:12px;">${formatCurrency(plan.amount, plan.currency)}</p>
        <div class="row" style="margin-top:16px;">
          <button type="button" data-plan-name="${plan.plan}" ${!plan.available || !user ? "disabled" : ""}>${buttonLabel}</button>
        </div>
      `;
      container.appendChild(card);
    });

    container.querySelectorAll("button[data-plan-name]").forEach((button) => {
      button.addEventListener("click", async () => {
        const authStatus = byId("auth-status");
        const phoneNumber = phoneInput?.value?.trim() || "";
        if (!phoneNumber) {
          setStatus(authStatus, "Enter the phone number that should receive the M-Pesa prompt.", true);
          return;
        }

        button.disabled = true;
        setStatus(authStatus, "Sending PayHero M-Pesa prompt...");
        try {
          const response = await authorizedFetch("/billing/payment-request", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              plan_name: button.dataset.planName,
              phone_number: phoneNumber,
            }),
          });
          const payload = await safeJson(response);
          if (!response.ok) {
            throw new Error(payload.detail || "Could not send the PayHero prompt.");
          }

          const refreshedUser = await loadCurrentUser().catch(() => user);
          renderAccount(refreshedUser);
          await renderBillingPlans(refreshedUser);
          setStatus(
            authStatus,
            `PayHero prompt queued for ${phoneNumber}. Reference: ${payload.reference || payload.external_reference}. Complete the M-Pesa prompt, then refresh payment status.`,
          );
        } catch (error) {
          setStatus(authStatus, error.message || "Could not start the payment request.", true);
          button.disabled = false;
        }
      });
    });
  } catch (error) {
    empty.hidden = false;
    empty.textContent = error.message || "Could not load billing plans.";
  }
};

const initAuthPage = () => {
  const signupForm = byId("signup-form");
  const loginForm = byId("login-form");
  const authStatus = byId("auth-status");
  if (!signupForm || !loginForm || !authStatus) {
    return;
  }

  const signupName = byId("signup-name");
  const signupEmail = byId("signup-email");
  const signupPassword = byId("signup-password");
  const signupSubmit = byId("signup-submit");
  const loginEmail = byId("login-email");
  const loginPassword = byId("login-password");
  const loginSubmit = byId("login-submit");
  const refreshPaymentButton = byId("refresh-payment-button");
  const signoutButton = byId("signout-button");

  const currentPaymentReference = () => {
    const auth = getStoredAuth();
    return auth?.user?.subscription?.payhero_reference || auth?.user?.subscription?.payhero_external_reference || null;
  };

  const refreshAccount = async () => {
    try {
      const user = await loadCurrentUser();
      renderAccount(user);
      await renderBillingPlans(user);
      return user;
    } catch (error) {
      renderAccount(null);
      await renderBillingPlans(null);
      setStatus(authStatus, error.message || "Could not load account.", true);
      return null;
    }
  };

  const refreshPaymentStatus = async () => {
    const reference = currentPaymentReference();
    if (!reference) {
      throw new Error("No PayHero payment reference is available for this account yet.");
    }

    const response = await authorizedFetch(`/billing/payment-status?reference=${encodeURIComponent(reference)}`);
    const payload = await safeJson(response);
    if (!response.ok) {
      throw new Error(payload.detail || "Could not refresh the latest payment status.");
    }

    const refreshedUser = await loadCurrentUser().catch(() => getStoredAuth()?.user || null);
    renderAccount(refreshedUser);
    await renderBillingPlans(refreshedUser);
    return payload;
  };

  const persistAuth = (payload) => {
    if (payload?.session?.access_token) {
      setStoredAuth({ session: payload.session, user: payload.user });
      renderAccount(payload.user);
    } else {
      clearStoredAuth();
      renderAccount(null);
    }
  };

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    signupSubmit.disabled = true;
    setStatus(authStatus, "Creating account...");
    try {
      const response = await fetch(API_BASE_URL + "/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: signupName.value.trim(),
          email: signupEmail.value.trim(),
          password: signupPassword.value,
        }),
      });
      const payload = await safeJson(response);
      if (!response.ok) {
        throw new Error(payload.detail || "Could not create account.");
      }

      signupForm.reset();
      persistAuth(payload);
      await renderBillingPlans(payload.user || null);
      setStatus(
        authStatus,
        payload.needs_email_confirmation
          ? "Account created. Check your inbox to confirm the email before signing in."
          : "Account created and signed in successfully.",
      );
    } catch (error) {
      setStatus(authStatus, error.message || "Could not create account.", true);
    } finally {
      signupSubmit.disabled = false;
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginSubmit.disabled = true;
    setStatus(authStatus, "Signing in...");
    try {
      const response = await fetch(API_BASE_URL + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: loginEmail.value.trim(),
          password: loginPassword.value,
        }),
      });
      const payload = await safeJson(response);
      if (!response.ok) {
        throw new Error(payload.detail || "Could not sign in.");
      }

      loginForm.reset();
      persistAuth(payload);
      await renderBillingPlans(payload.user || null);
      setStatus(authStatus, `Signed in as ${payload.user.email}.`);
    } catch (error) {
      setStatus(authStatus, error.message || "Could not sign in.", true);
    } finally {
      loginSubmit.disabled = false;
    }
  });

  refreshPaymentButton?.addEventListener("click", async () => {
    refreshPaymentButton.disabled = true;
    setStatus(authStatus, "Refreshing PayHero payment status...");
    try {
      const payload = await refreshPaymentStatus();
      setStatus(
        authStatus,
        payload.status === "SUCCESS"
          ? "Payment confirmed successfully."
          : `Latest payment status: ${payload.status || "unknown"}.`,
      );
    } catch (error) {
      setStatus(authStatus, error.message || "Could not refresh payment status.", true);
      refreshPaymentButton.disabled = false;
    }
  });

  signoutButton?.addEventListener("click", async () => {
    clearStoredAuth();
    renderAccount(null);
    await renderBillingPlans(null);
    setStatus(authStatus, "Signed out locally.");
  });

  refreshAccount();
};

const initAdminPage = () => {
  const status = byId("admin-status");
  const badge = byId("admin-access-badge");
  const usersContainer = byId("admin-users");
  const leadsContainer = byId("admin-leads");
  const usersEmpty = byId("admin-users-empty");
  const leadsEmpty = byId("admin-leads-empty");
  const userCount = byId("admin-user-count");
  const leadCount = byId("admin-lead-count");
  const subscriptionCount = byId("admin-subscription-count");

  if (!status || !badge || !usersContainer || !leadsContainer) {
    return;
  }

  const renderUsers = (users) => {
    renderCardList(usersContainer, users, (user) => {
      const card = document.createElement("article");
      card.className = "lead-card";
      card.innerHTML = `
        <div class="lead-top">
          <div>
            <h3>${user.full_name || user.email || "Unknown user"}</h3>
            <div class="take-meta">${user.email || "No email"}</div>
          </div>
          <div class="take-meta">${user.role}</div>
        </div>
        <div class="take-meta">Created: ${user.created_at ? formatDate(user.created_at) : "Unknown"}</div>
        <div class="take-meta">Email confirmed: ${user.email_confirmed_at ? formatDate(user.email_confirmed_at) : "No"}</div>
        <div class="take-meta">Payment: ${user.subscription?.status || "No payment"}</div>
      `;
      return card;
    });
    usersEmpty.hidden = users.length > 0;
  };

  const renderLeads = (leads) => {
    renderCardList(leadsContainer, leads, (lead) => {
      const card = document.createElement("article");
      card.className = "lead-card";
      card.innerHTML = `
        <div class="lead-top">
          <div>
            <h3>${lead.organization}</h3>
            <div class="take-meta">${lead.contact_name} - ${lead.email}</div>
          </div>
          <div class="take-meta">${formatDate(lead.submitted_at)}</div>
        </div>
        <div class="take-meta">Choir type: ${lead.choir_type || "Not provided"}</div>
        <div class="take-meta">Choir size: ${lead.choir_size || "Not provided"}</div>
        <div class="take-meta">${lead.notes || "No setup notes yet."}</div>
      `;
      return card;
    });
    leadsEmpty.hidden = leads.length > 0;
  };

  const loadOverview = async () => {
    let currentUser = null;
    try {
      currentUser = await loadCurrentUser();
    } catch (error) {
      setStatus(status, error.message || "Could not load the current account.", true);
      badge.textContent = "Unavailable";
      return;
    }

    if (!currentUser) {
      setStatus(status, "Sign in on the Auth route with an admin account first.", true);
      badge.textContent = "Logged out";
      return;
    }

    if (currentUser.role !== "admin") {
      setStatus(status, "This account is authenticated, but it is not marked as an admin.", true);
      badge.textContent = "Access denied";
      return;
    }

    badge.textContent = "Admin verified";
    badge.classList.add("alt");
    setStatus(status, "Loading admin overview...");

    try {
      const response = await authorizedFetch("/admin/overview");
      const payload = await safeJson(response);
      if (!response.ok) {
        throw new Error(payload.detail || "Could not load admin overview.");
      }

      const users = Array.isArray(payload.users) ? payload.users : [];
      const leads = Array.isArray(payload.leads) ? payload.leads : [];
      renderUsers(users);
      renderLeads(leads);
      userCount.textContent = `${payload.counts?.users || users.length}`;
      leadCount.textContent = `${payload.counts?.leads || leads.length}`;
      subscriptionCount.textContent = `${users.filter((user) => user.subscription?.status).length}`;
      setStatus(status, `Loaded ${users.length} users and ${leads.length} pilot leads.`);
    } catch (error) {
      setStatus(status, error.message || "Could not load admin overview.", true);
      badge.textContent = "Error";
    }
  };

  loadOverview();
};

const initHomeStats = () => {
  const takeCount = byId("home-take-count");
  if (!takeCount) {
    return;
  }

  fetch(API_BASE_URL + "/voice-takes")
    .then((response) => response.json())
    .then((takes) => {
      takeCount.textContent = `${Array.isArray(takes) ? takes.length : 0}`;
    })
    .catch(() => {
      takeCount.textContent = "0";
    });
};

document.addEventListener("DOMContentLoaded", () => {
  initHomeStats();
  initPracticePage();
  initStudioPage();
  initPilotPage();
  initAuthPage();
  initAdminPage();
});
