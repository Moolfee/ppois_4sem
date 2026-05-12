const state = {
  data: null,
};

const els = {
  message: document.querySelector("#message"),
  current: document.querySelector("#status-current"),
  playback: document.querySelector("#status-playback"),
  volume: document.querySelector("#status-volume"),
  brightness: document.querySelector("#status-brightness"),
  library: document.querySelector("#status-library"),
  playlists: document.querySelector("#status-playlists"),
  volumeInput: document.querySelector("#volume-input"),
  brightnessInput: document.querySelector("#brightness-input"),
  formatSelect: document.querySelector("#video-format-select"),
  formats: document.querySelector("#formats-list"),
  videos: document.querySelector("#videos-list"),
  playlistsList: document.querySelector("#playlists-list"),
};

function setMessage(text, kind = "ok") {
  els.message.textContent = text;
  els.message.className = `message ${kind}`;
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail || response.statusText;
    throw new Error(Array.isArray(detail) ? detail[0]?.msg || "Request error" : detail);
  }
  return payload;
}

async function loadState() {
  try {
    state.data = await request("/api/state");
    render();
    setMessage("Состояние обновлено");
  } catch (error) {
    setMessage(error.message, "error");
  }
}

async function mutate(path, options, okText) {
  try {
    state.data = await request(path, options);
    render();
    setMessage(okText);
    return true;
  } catch (error) {
    setMessage(error.message, "error");
    return false;
  }
}

function render() {
  const data = state.data;
  if (!data) {
    return;
  }

  els.current.textContent = data.status.current_video || "Нет";
  els.playback.textContent = data.status.playback;
  els.volume.textContent = data.status.volume;
  els.brightness.textContent = data.status.brightness;
  els.library.textContent = data.status.library_size;
  els.playlists.textContent = data.status.playlists_size;
  els.volumeInput.value = data.status.volume;
  els.brightnessInput.value = data.status.brightness;

  renderFormatSelect(data.supported_formats);

  els.formats.replaceChildren(
    ...data.supported_formats.map((format) => {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = format;
      return chip;
    }),
  );

  renderVideos(data.videos);
  renderPlaylists(data.playlists, data.videos);
}

function renderFormatSelect(formats) {
  const currentValue = els.formatSelect.value;

  els.formatSelect.replaceChildren(
    ...formats.map((format) => {
      const option = document.createElement("option");
      option.value = format;
      option.textContent = format;
      return option;
    }),
  );

  els.formatSelect.disabled = formats.length === 0;
  if (formats.includes(currentValue)) {
    els.formatSelect.value = currentValue;
  }
}

function renderVideos(videos) {
  if (!videos.length) {
    els.videos.innerHTML = '<div class="empty">Библиотека пуста</div>';
    return;
  }

  els.videos.replaceChildren(
    ...videos.map((video) => {
      const item = document.createElement("article");
      item.className = "list-item";
      item.innerHTML = `
        <div class="item-main">
          <div class="item-title">
            <strong></strong>
            <span></span>
          </div>
          <div class="item-actions">
            <button class="compact" type="button" data-video-select>Выбрать</button>
            <button class="compact danger" type="button" data-video-remove>Удалить</button>
          </div>
        </div>
      `;
      item.querySelector("strong").textContent = video.title;
      item.querySelector("span").textContent =
        `${video.format_ext}, ${video.duration_seconds}s`;
      item.querySelector("[data-video-select]").addEventListener("click", () => {
        mutate(
          `/api/videos/${encodeURIComponent(video.title)}/select`,
          { method: "POST" },
          `Выбрано видео: ${video.title}`,
        );
      });
      item.querySelector("[data-video-remove]").addEventListener("click", () => {
        mutate(
          `/api/videos/${encodeURIComponent(video.title)}`,
          { method: "DELETE" },
          `Видео удалено: ${video.title}`,
        );
      });
      return item;
    }),
  );
}

function renderPlaylists(playlists, videos) {
  if (!playlists.length) {
    els.playlistsList.innerHTML = '<div class="empty">Плейлистов нет</div>';
    return;
  }

  els.playlistsList.replaceChildren(
    ...playlists.map((playlist) => {
      const item = document.createElement("article");
      item.className = "list-item";

      const options = videos
        .map(
          (video) =>
            `<option value="${escapeAttribute(video.title)}">${escapeHtml(
              video.title,
            )}</option>`,
        )
        .join("");

      item.innerHTML = `
        <div class="item-main">
          <div class="item-title">
            <strong></strong>
            <span>${playlist.videos.length} видео</span>
          </div>
        </div>
        <form class="playlist-add">
          <select name="title" ${videos.length ? "" : "disabled"}>${options}</select>
          <button type="submit" ${videos.length ? "" : "disabled"}>Добавить</button>
        </form>
        <div class="playlist-videos"></div>
      `;
      item.querySelector("strong").textContent = playlist.name;

      item.querySelector(".playlist-add").addEventListener("submit", (event) => {
        event.preventDefault();
        const title = new FormData(event.currentTarget).get("title");
        mutate(
          `/api/playlists/${encodeURIComponent(playlist.name)}/videos/${encodeURIComponent(title)}`,
          { method: "POST" },
          `Добавлено в плейлист: ${title}`,
        );
      });

      const videosBox = item.querySelector(".playlist-videos");
      if (!playlist.videos.length) {
        videosBox.innerHTML = '<div class="empty">Плейлист пуст</div>';
      } else {
        videosBox.replaceChildren(
          ...playlist.videos.map((video) => playlistVideoRow(playlist.name, video)),
        );
      }

      return item;
    }),
  );
}

function playlistVideoRow(playlistName, video) {
  const row = document.createElement("div");
  row.className = "item-main";
  row.innerHTML = `
    <div class="item-title">
      <strong></strong>
      <span></span>
    </div>
    <div class="item-actions">
      <button class="compact" type="button" data-playlist-select>Выбрать</button>
      <button class="compact danger" type="button" data-playlist-remove>Удалить</button>
    </div>
  `;
  row.querySelector("strong").textContent = video.title;
  row.querySelector("span").textContent =
    `${video.format_ext}, ${video.duration_seconds}s`;
  row.querySelector("[data-playlist-select]").addEventListener("click", () => {
    mutate(
      `/api/playlists/${encodeURIComponent(playlistName)}/videos/${encodeURIComponent(video.title)}/select`,
      { method: "POST" },
      `Выбрано из плейлиста: ${video.title}`,
    );
  });
  row.querySelector("[data-playlist-remove]").addEventListener("click", () => {
    mutate(
      `/api/playlists/${encodeURIComponent(playlistName)}/videos/${encodeURIComponent(video.title)}`,
      { method: "DELETE" },
      `Удалено из плейлиста: ${video.title}`,
    );
  });
  return row;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("'", "&#039;");
}

document.querySelector("#refresh-state").addEventListener("click", loadState);

document.querySelector("#video-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const payload = {
    title: String(formData.get("title")).trim(),
    format_ext: String(formData.get("format_ext")).trim(),
    duration_seconds: Number(formData.get("duration_seconds")),
  };
  mutate(
    "/api/videos",
    { method: "POST", body: JSON.stringify(payload) },
    `Видео добавлено: ${payload.title}`,
  ).then((ok) => {
    if (ok) {
      form.reset();
      renderFormatSelect(state.data.supported_formats);
    }
  });
});

document.querySelector("#playlist-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {
    name: String(new FormData(form).get("name")).trim(),
  };
  mutate(
    "/api/playlists",
    { method: "POST", body: JSON.stringify(payload) },
    `Плейлист создан: ${payload.name}`,
  ).then((ok) => {
    if (ok) {
      form.reset();
    }
  });
});

document.querySelectorAll("[data-playback]").forEach((button) => {
  button.addEventListener("click", () => {
    const action = button.dataset.playback;
    mutate(`/api/playback/${action}`, { method: "POST" }, `Команда: ${action}`);
  });
});

els.volumeInput.addEventListener("change", () => {
  mutate(
    "/api/settings/volume",
    { method: "PUT", body: JSON.stringify({ value: Number(els.volumeInput.value) }) },
    `Громкость: ${els.volumeInput.value}`,
  );
});

els.brightnessInput.addEventListener("change", () => {
  mutate(
    "/api/settings/brightness",
    {
      method: "PUT",
      body: JSON.stringify({ value: Number(els.brightnessInput.value) }),
    },
    `Яркость: ${els.brightnessInput.value}`,
  );
});

loadState();
