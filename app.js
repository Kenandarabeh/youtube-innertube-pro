/**
 * InnerTube Pro ⚡ - Modern Client Controller
 * ----------------------------------------------------
 * High-performance JavaScript controller interfacing with the InnerTube daemon
 * - Infinite scroll pagination via InnerTube continuation tokens
 * - Universal link inspection & multi-quality stream extraction
 * - Cinema theater watch view & floating PiP mini-player
 * - Shorts 9:16 vertical reel runner & trending categories
 */

document.addEventListener('DOMContentLoaded', () => {

  // ==========================================
  // 1. STATE MANAGEMENT
  // ==========================================
  const state = {
    currentView: 'home',
    currentQuery: 'technology trending 2026',
    continuationToken: null,
    currentPage: 1,
    isLoading: false,
    hasMore: true,
    currentVideo: null,
    shortsList: [],
    currentShortIndex: 0,
    trendingTab: 'general',
    trendingContinuation: null,
    trendingPage: 1,
    isTrendingLoading: false,
    history: JSON.parse(localStorage.getItem('it_history') || '[]'),
    subscriptions: JSON.parse(localStorage.getItem('it_subs') || '["Google DeepMind", "Veritasium", "MKBHD", "Fireship"]')
  };

  // ==========================================
  // 2. DOM REFERENCES
  // ==========================================
  const brandLogo = document.getElementById('brandLogo');
  const menuToggle = document.getElementById('menuToggle');
  const mainSidebar = document.getElementById('mainSidebar');
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const quickLinkToolBtn = document.getElementById('quickLinkToolBtn');

  // Search
  const searchForm = document.getElementById('searchForm');
  const searchInput = document.getElementById('searchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');

  // Views
  const views = {
    home: document.getElementById('viewHome'),
    shorts: document.getElementById('viewShorts'),
    trending: document.getElementById('viewTrending'),
    downloader: document.getElementById('viewDownloader'),
    channel: document.getElementById('viewChannel'),
    library: document.getElementById('viewLibrary')
  };

  // Nav Items
  const navItems = {
    home: document.getElementById('navHome'),
    shorts: document.getElementById('navShorts'),
    trending: document.getElementById('navTrending'),
    downloader: document.getElementById('navDownloader'),
    subs: document.getElementById('navSubs'),
    library: document.getElementById('navLibrary'),
    history: document.getElementById('navHistory')
  };

  // Home & Infinite Scroll
  const chipsContainer = document.getElementById('chipsContainer');
  const homeVideoGrid = document.getElementById('homeVideoGrid');
  const infiniteLoader = document.getElementById('infiniteLoader');

  // Trending
  const trendingTabs = document.getElementById('trendingTabs');
  const trendingVideoGrid = document.getElementById('trendingVideoGrid');
  const trendingLoader = document.getElementById('trendingLoader');

  // Link Downloader Tool
  const inspectForm = document.getElementById('inspectForm');
  const inspectUrlInput = document.getElementById('inspectUrlInput');
  const pasteClipboardBtn = document.getElementById('pasteClipboardBtn');
  const inspectSubmitBtn = document.getElementById('inspectSubmitBtn');
  const inspectResultContainer = document.getElementById('inspectResultContainer');

  // Shorts Viewer
  const shortsIframe = document.getElementById('shortsIframe');
  const shortsTitle = document.getElementById('shortsTitle');
  const shortsChannel = document.getElementById('shortsChannel');
  const shortsSubBtn = document.getElementById('shortsSubBtn');
  const shortsLikeBtn = document.getElementById('shortsLikeBtn');
  const shortsDownloadBtn = document.getElementById('shortsDownloadBtn');
  const shortsNextBtn = document.getElementById('shortsNextBtn');
  const shortsPrevBtn = document.getElementById('shortsPrevBtn');

  // Cinema Watch Room
  const cinemaWatchView = document.getElementById('cinemaWatchView');
  const cinemaIframe = document.getElementById('cinemaIframe');
  const cinemaTitle = document.getElementById('cinemaTitle');
  const cinemaChannelName = document.getElementById('cinemaChannelName');
  const cinemaChannelAvatar = document.getElementById('cinemaChannelAvatar');
  const cinemaSubBtn = document.getElementById('cinemaSubBtn');
  const cinemaViews = document.getElementById('cinemaViews');
  const cinemaDate = document.getElementById('cinemaDate');
  const cinemaLikeBtn = document.getElementById('cinemaLikeBtn');
  const cinemaDownloadBtn = document.getElementById('cinemaDownloadBtn');
  const cinemaShareBtn = document.getElementById('cinemaShareBtn');
  const closeCinemaBtn = document.getElementById('closeCinemaBtn');
  const relatedVideosList = document.getElementById('relatedVideosList');
  const commentInput = document.getElementById('commentInput');
  const commentSendBtn = document.getElementById('commentSendBtn');
  const commentsList = document.getElementById('commentsList');

  // Download Modal
  const downloadModal = document.getElementById('downloadModal');
  const closeDownloadModalBtn = document.getElementById('closeDownloadModalBtn');
  const downloadThumb = document.getElementById('downloadThumb');
  const downloadTitle = document.getElementById('downloadTitle');
  const downloadChannel = document.getElementById('downloadChannel');
  const downloadFormatsList = document.getElementById('downloadFormatsList');

  // PiP Mini Player
  const pipPlayer = document.getElementById('pipPlayer');
  const pipIframe = document.getElementById('pipIframe');
  const pipTitle = document.getElementById('pipTitle');
  const pipExpandBtn = document.getElementById('pipExpandBtn');
  const pipCloseBtn = document.getElementById('pipCloseBtn');

  // Toast Container
  const toastContainer = document.getElementById('toastContainer');

  // ==========================================
  // 3. TOAST NOTIFICATION UTILITY
  // ==========================================
  function showToast(message, duration = 3500) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span>⚡</span> <span>${message}</span>`;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(12px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // ==========================================
  // 4. VIEW ROUTER
  // ==========================================
  function switchView(targetView) {
    state.currentView = targetView;

    // Toggle panels
    Object.keys(views).forEach(key => {
      if (views[key]) {
        views[key].style.display = (key === targetView) ? 'block' : 'none';
        views[key].classList.toggle('active', key === targetView);
      }
    });

    // Toggle nav items
    Object.keys(navItems).forEach(key => {
      if (navItems[key]) navItems[key].classList.remove('active');
    });

    if (targetView === 'home' && navItems.home) navItems.home.classList.add('active');
    if (targetView === 'shorts' && navItems.shorts) navItems.shorts.classList.add('active');
    if (targetView === 'trending' && navItems.trending) navItems.trending.classList.add('active');
    if (targetView === 'downloader' && navItems.downloader) navItems.downloader.classList.add('active');
    if (targetView === 'library' && navItems.library) navItems.library.classList.add('active');

    // Trigger loads if empty
    if (targetView === 'shorts' && state.shortsList.length === 0) {
      loadShortsFeed();
    } else if (targetView === 'trending' && trendingVideoGrid.children.length === 0) {
      loadTrendingVideos(true);
    } else if (targetView === 'library') {
      renderHistoryView();
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Nav click handlers
  navItems.home.addEventListener('click', (e) => { e.preventDefault(); switchView('home'); });
  navItems.shorts.addEventListener('click', (e) => { e.preventDefault(); switchView('shorts'); });
  navItems.trending.addEventListener('click', (e) => { e.preventDefault(); switchView('trending'); });
  navItems.downloader.addEventListener('click', (e) => { e.preventDefault(); switchView('downloader'); });
  navItems.library.addEventListener('click', (e) => { e.preventDefault(); switchView('library'); });
  navItems.history.addEventListener('click', (e) => { e.preventDefault(); switchView('library'); });
  quickLinkToolBtn.addEventListener('click', () => switchView('downloader'));
  brandLogo.addEventListener('click', (e) => { e.preventDefault(); switchView('home'); });

  // Sidebar toggle
  menuToggle.addEventListener('click', () => {
    mainSidebar.classList.toggle('collapsed');
  });

  // Theme toggle
  themeToggleBtn.addEventListener('click', () => {
    document.body.classList.toggle('light-theme');
    const isLight = document.body.classList.contains('light-theme');
    showToast(isLight ? 'Switched to Clean Light Mode' : 'Switched to Luxury Dark Mode');
  });

  // ==========================================
  // 5. HOME FEED & INFINITE SCROLL
  // ==========================================
  async function loadHomeVideos(reset = false) {
    if (state.isLoading) return;
    state.isLoading = true;

    if (reset) {
      state.currentPage = 1;
      state.continuationToken = null;
      state.hasMore = true;
      homeVideoGrid.innerHTML = '';
    }

    infiniteLoader.style.display = 'flex';

    try {
      let url = `/api/search?q=${encodeURIComponent(state.currentQuery)}&page=${state.currentPage}`;
      if (state.continuationToken) {
        url += `&continuation=${encodeURIComponent(state.continuationToken)}`;
      }

      const res = await fetch(url);
      const data = await res.json();

      infiniteLoader.style.display = 'none';
      state.isLoading = false;

      if (data.videos && data.videos.length > 0) {
        renderVideoCards(data.videos, homeVideoGrid);
        state.continuationToken = data.continuation;
        state.currentPage++;
      } else {
        state.hasMore = false;
        if (reset) {
          homeVideoGrid.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-secondary);">No videos found for this topic.</div>';
        }
      }
    } catch (err) {
      infiniteLoader.style.display = 'none';
      state.isLoading = false;
      showToast('Error querying InnerTube gateway');
    }
  }

  function renderVideoCards(videos, container) {
    videos.forEach(video => {
      const card = document.createElement('div');
      card.className = 'video-card';
      card.innerHTML = `
        <div class="thumbnail-wrapper">
          <img src="${video.thumbnail || `https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`}" alt="${escapeHtml(video.title)}" loading="lazy">
          <span class="duration-badge">${video.duration || '10:00'}</span>
        </div>
        <div class="video-card-body">
          <div class="channel-avatar">${(video.channel || 'Y').charAt(0).toUpperCase()}</div>
          <div class="video-meta-info">
            <h3 class="video-title" title="${escapeHtml(video.title)}">${escapeHtml(video.title)}</h3>
            <div class="channel-name">${escapeHtml(video.channel || 'YouTube Creator')}</div>
            <div class="video-stats">${video.views || '15K views'} • ${video.published || 'Recently'}</div>
          </div>
        </div>
      `;

      card.addEventListener('click', () => openCinemaWatch(video));
      container.appendChild(card);
    });
  }

  // Infinite Scroll Listener
  window.addEventListener('scroll', () => {
    if (state.currentView !== 'home' && state.currentView !== 'trending') return;
    const scrollPos = window.innerHeight + window.scrollY;
    const threshold = document.documentElement.offsetHeight - 800;

    if (scrollPos >= threshold && !state.isLoading && state.hasMore) {
      if (state.currentView === 'home') {
        loadHomeVideos(false);
      } else if (state.currentView === 'trending' && !state.isTrendingLoading) {
        loadTrendingVideos(false);
      }
    }
  });

  // Filter Chips
  chipsContainer.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;

    chipsContainer.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');

    state.currentQuery = chip.dataset.query === 'all' ? 'technology trending 2026' : chip.dataset.query;
    loadHomeVideos(true);
  });

  // Search Form
  searchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = searchInput.value.trim();
    if (!query) return;

    state.currentQuery = query;
    switchView('home');
    loadHomeVideos(true);
  });

  searchInput.addEventListener('input', () => {
    clearSearchBtn.style.display = searchInput.value.length > 0 ? 'block' : 'none';
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    searchInput.focus();
  });

  // ==========================================
  // 6. TRENDING CATEGORIES
  // ==========================================
  async function loadTrendingVideos(reset = false) {
    if (state.isTrendingLoading) return;
    state.isTrendingLoading = true;

    if (reset) {
      state.trendingPage = 1;
      state.trendingContinuation = null;
      trendingVideoGrid.innerHTML = '';
    }

    trendingLoader.style.display = 'flex';

    try {
      let url = `/api/trending?tab=${state.trendingTab}&page=${state.trendingPage}`;
      if (state.trendingContinuation) {
        url += `&continuation=${encodeURIComponent(state.trendingContinuation)}`;
      }

      const res = await fetch(url);
      const data = await res.json();

      trendingLoader.style.display = 'none';
      state.isTrendingLoading = false;

      if (data.videos && data.videos.length > 0) {
        renderVideoCards(data.videos, trendingVideoGrid);
        state.trendingContinuation = data.continuation;
        state.trendingPage++;
      }
    } catch (err) {
      trendingLoader.style.display = 'none';
      state.isTrendingLoading = false;
    }
  }

  trendingTabs.addEventListener('click', (e) => {
    const tab = e.target.closest('.trending-tab');
    if (!tab) return;

    trendingTabs.querySelectorAll('.trending-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');

    state.trendingTab = tab.dataset.tab;
    loadTrendingVideos(true);
  });

  // ==========================================
  // 7. UNIVERSAL LINK INSPECTOR & DOWNLOADER
  // ==========================================
  inspectForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const urlOrId = inspectUrlInput.value.trim();
    if (!urlOrId) return;

    inspectSubmitBtn.disabled = true;
    inspectSubmitBtn.innerHTML = '<div class="loader-spinner" style="width:16px;height:16px;"></div> <span>Inspecting...</span>';
    inspectResultContainer.innerHTML = `
      <div style="padding:40px;text-align:center;">
        <div class="loader-spinner" style="margin:0 auto 16px;"></div>
        <p style="color:var(--text-secondary);">Querying YouTube InnerTube & resolving stream descriptors...</p>
      </div>
    `;

    try {
      const res = await fetch(`/api/inspect_link?url=${encodeURIComponent(urlOrId)}`);
      const data = await res.json();

      inspectSubmitBtn.disabled = false;
      inspectSubmitBtn.innerHTML = '<span>Inspect Link ⚡</span>';

      if (data.status === 'success') {
        renderInspectResult(data);
      } else {
        inspectResultContainer.innerHTML = `
          <div style="padding:24px;background:rgba(255,0,51,0.1);border:1px solid rgba(255,0,51,0.3);border-radius:16px;color:#FF738F;">
            ⚠️ ${data.message || 'Could not inspect link. Verify that the URL is public and valid.'}
          </div>
        `;
      }
    } catch (err) {
      inspectSubmitBtn.disabled = false;
      inspectSubmitBtn.innerHTML = '<span>Inspect Link ⚡</span>';
      inspectResultContainer.innerHTML = '<div style="padding:20px;color:#FF5555;">Server communication error.</div>';
    }
  });

  pasteClipboardBtn.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        inspectUrlInput.value = text;
        showToast('Link pasted from clipboard 📋');
        inspectForm.dispatchEvent(new Event('submit'));
      }
    } catch (err) {
      inspectUrlInput.focus();
      showToast('Press Ctrl+V to paste your link');
    }
  });

  function renderInspectResult(data) {
    inspectResultContainer.innerHTML = `
      <div class="inspected-media-card">
        <div class="inspected-thumb-box">
          <img src="${data.thumbnail}" alt="Thumbnail">
        </div>
        <div class="inspected-details-col">
          <div>
            <h2 class="inspected-title">${escapeHtml(data.title)}</h2>
            <div class="inspected-meta-row">
              <span>👤 <strong>${escapeHtml(data.channel)}</strong></span>
              <span>⏱️ ${data.duration}</span>
              <span>👁️ ${data.views}</span>
            </div>
          </div>
          <button class="watch-now-action-btn" id="inspectWatchBtn">
            <span>🎬 Watch in Cinema Player</span>
          </button>
        </div>
      </div>
      <h3 class="section-title">Available Stream Qualities & Formats</h3>
    `;

    // Watch button event
    document.getElementById('inspectWatchBtn').addEventListener('click', () => {
      openCinemaWatch({
        id: data.id,
        title: data.title,
        channel: data.channel,
        duration: data.duration,
        views: data.views,
        thumbnail: data.thumbnail
      });
    });

    // Render Qualities Grid
    const qGrid = document.createElement('div');
    qGrid.className = 'qualities-grid-container';

    data.qualities.forEach(q => {
      const qCard = document.createElement('div');
      qCard.className = 'quality-card';
      qCard.innerHTML = `
        <div class="quality-card-header">
          <span class="quality-card-title">${escapeHtml(q.label)}</span>
          <span class="download-badge">${q.badge || q.quality}</span>
        </div>
        <div class="quality-card-actions">
          <button class="q-action-btn q-btn-pc" title="Save directly to ~/Downloads">
            <span>💻 Save to PC</span>
          </button>
          <a class="q-action-btn q-btn-browser" href="/api/stream_download?id=${data.id}&type=${q.type}&quality=${q.quality}&title=${encodeURIComponent(data.title)}" target="_blank" title="Stream via browser">
            <span>🌐 Browser</span>
          </a>
        </div>
      `;

      // Direct PC download handler
      const pcBtn = qCard.querySelector('.q-btn-pc');
      pcBtn.addEventListener('click', () => {
        executeDirectDownload(data.id, q.type, q.quality, data.title, pcBtn);
      });

      // Browser download feedback
      const browserBtn = qCard.querySelector('.q-btn-browser');
      if (browserBtn) {
        browserBtn.addEventListener('click', () => {
          showToast(`Initiating browser stream for ${q.label} 🌐...`);
        });
      }

      qGrid.appendChild(qCard);
    });

    inspectResultContainer.appendChild(qGrid);
    showToast('All stream formats & qualities extracted successfully! 🎯');
  }

  // ==========================================
  // 8. SHORTS VIEWER (9:16 VERTICAL REELS)
  // ==========================================
  async function loadShortsFeed() {
    try {
      const res = await fetch('/api/shorts?q=shorts%20viral');
      const data = await res.json();
      if (data.shorts && data.shorts.length > 0) {
        state.shortsList = data.shorts;
        state.currentShortIndex = 0;
        displayShort(0);
      }
    } catch (err) {
      showToast('Could not load Shorts feed');
    }
  }

  function displayShort(index) {
    if (!state.shortsList[index]) return;
    const short = state.shortsList[index];

    shortsIframe.src = `https://www.youtube.com/embed/${short.id}?autoplay=1&loop=1&playlist=${short.id}`;
    shortsTitle.textContent = short.title;
    shortsChannel.textContent = short.channel;
  }

  shortsNextBtn.addEventListener('click', () => {
    if (state.currentShortIndex < state.shortsList.length - 1) {
      state.currentShortIndex++;
      displayShort(state.currentShortIndex);
    } else {
      showToast('Fetching more shorts...');
      loadShortsFeed();
    }
  });

  shortsPrevBtn.addEventListener('click', () => {
    if (state.currentShortIndex > 0) {
      state.currentShortIndex--;
      displayShort(state.currentShortIndex);
    }
  });

  shortsLikeBtn.addEventListener('click', () => {
    shortsLikeBtn.style.color = 'var(--accent-red)';
    showToast('Liked Short ❤️');
  });

  shortsDownloadBtn.addEventListener('click', () => {
    const currentShort = state.shortsList[state.currentShortIndex];
    if (currentShort) {
      openDownloadModal(currentShort);
    }
  });

  // ==========================================
  // 9. CINEMA WATCH ROOM & EMBEDDED PLAYER
  // ==========================================
  function openCinemaWatch(video) {
    state.currentVideo = video;
    cinemaTitle.textContent = video.title;
    cinemaChannelName.textContent = video.channel;
    cinemaChannelAvatar.textContent = (video.channel || 'C').charAt(0).toUpperCase();
    cinemaViews.textContent = video.views || '15K views';
    cinemaDate.textContent = video.published || 'Recently published';

    // Embed YouTube player
    cinemaIframe.src = `https://www.youtube.com/embed/${video.id}?autoplay=1&rel=0`;
    cinemaWatchView.style.display = 'block';
    document.body.style.overflow = 'hidden';

    // Save to history
    addToHistory(video);

    // Fetch related videos
    fetchRelatedVideos(video.id, video.title);

    // Render simulated comments
    renderComments();

    // Query SponsorBlock segments
    fetch(`/api/sponsorblock?id=${video.id}`)
      .then(res => res.json())
      .then(sb => {
        if (sb.segments && sb.segments.length > 0) {
          showToast(`🛡️ SponsorBlock: ${sb.segments.length} sponsored segment(s) detected!`);
        }
      })
      .catch(() => {});
  }

  function closeCinemaWatch() {
    cinemaWatchView.style.display = 'none';
    cinemaIframe.src = '';
    document.body.style.overflow = 'auto';
  }

  closeCinemaBtn.addEventListener('click', closeCinemaWatch);

  cinemaLikeBtn.addEventListener('click', () => {
    cinemaLikeBtn.classList.toggle('active');
    showToast('Saved to Liked Videos 👍');
  });

  cinemaShareBtn.addEventListener('click', () => {
    if (navigator.clipboard && state.currentVideo) {
      navigator.clipboard.writeText(`https://www.youtube.com/watch?v=${state.currentVideo.id}`);
      showToast('Link copied to clipboard 📋');
    }
  });

  cinemaDownloadBtn.addEventListener('click', () => {
    if (state.currentVideo) {
      openDownloadModal(state.currentVideo);
    }
  });

  async function fetchRelatedVideos(id, title) {
    relatedVideosList.innerHTML = '<div style="padding:15px;text-align:center;"><div class="loader-spinner" style="margin:0 auto 8px;"></div><span>Finding recommendations...</span></div>';
    try {
      const res = await fetch(`/api/related?id=${id}&q=${encodeURIComponent(title)}`);
      const data = await res.json();
      relatedVideosList.innerHTML = '';

      if (data.related && data.related.length > 0) {
        data.related.slice(0, 10).forEach(item => {
          const card = document.createElement('div');
          card.className = 'related-card';
          card.innerHTML = `
            <div class="related-thumb">
              <img src="${item.thumbnail || `https://i.ytimg.com/vi/${item.id}/hqdefault.jpg`}" alt="${escapeHtml(item.title)}">
            </div>
            <div class="related-info">
              <h4 class="related-title">${escapeHtml(item.title)}</h4>
              <div class="related-channel">${escapeHtml(item.channel)}</div>
            </div>
          `;
          card.addEventListener('click', () => openCinemaWatch(item));
          relatedVideosList.appendChild(card);
        });
      }
    } catch (err) {
      relatedVideosList.innerHTML = '<div style="color:var(--text-muted);">No recommendations available.</div>';
    }
  }

  function renderComments() {
    const mockComments = [
      { author: 'Sarah Jenkins', time: '2 hours ago', text: 'Incredible audio clarity! Love the clean player.' },
      { author: 'TechLead_Global', time: '5 hours ago', text: 'The reverse engineering behind this InnerTube implementation is top-notch.' },
      { author: 'Alex Rivera', time: '1 day ago', text: 'Downloads straight to 1080p without buffering. Brilliant work!' }
    ];

    commentsList.innerHTML = '';
    mockComments.forEach(c => {
      const item = document.createElement('div');
      item.className = 'comment-item';
      item.innerHTML = `
        <div class="channel-pill-avatar" style="background:#2A2A3C;color:#FFF;">${c.author.charAt(0)}</div>
        <div class="comment-item-body">
          <div class="comment-author-row">
            <span class="comment-author">${escapeHtml(c.author)}</span>
            <span class="comment-time">${c.time}</span>
          </div>
          <p class="comment-text">${escapeHtml(c.text)}</p>
        </div>
      `;
      commentsList.appendChild(item);
    });
  }

  commentSendBtn.addEventListener('click', () => {
    const text = commentInput.value.trim();
    if (!text) return;

    const item = document.createElement('div');
    item.className = 'comment-item';
    item.innerHTML = `
      <div class="channel-pill-avatar" style="background:var(--accent-red);color:#FFF;">Y</div>
      <div class="comment-item-body">
        <div class="comment-author-row">
          <span class="comment-author">You</span>
          <span class="comment-time">Just now</span>
        </div>
        <p class="comment-text">${escapeHtml(text)}</p>
      </div>
    `;
    commentsList.prepend(item);
    commentInput.value = '';
    showToast('Comment posted! 💬');
  });

  // ==========================================
  // 10. MULTI-QUALITY DOWNLOAD MODAL & ENGINE
  // ==========================================
  function openDownloadModal(video) {
    downloadTitle.textContent = video.title;
    downloadChannel.textContent = video.channel;
    downloadThumb.src = video.thumbnail || `https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`;
    downloadModal.style.display = 'flex';
    downloadFormatsList.innerHTML = '<div style="padding:20px;text-align:center;"><div class="loader-spinner" style="margin:0 auto 10px;"></div><span>Fetching stream formats from InnerTube...</span></div>';

    fetch(`/api/download?id=${video.id}&title=${encodeURIComponent(video.title)}`)
      .then(res => res.json())
      .then(data => {
        downloadFormatsList.innerHTML = '';

        // Section 1: Save directly to ~/Downloads
        const heading1 = document.createElement('div');
        heading1.className = 'download-section-title';
        heading1.innerHTML = '💻 Save Directly to Your Computer (~/Downloads):';
        downloadFormatsList.appendChild(heading1);

        data.qualities.forEach(q => {
          const btn = document.createElement('button');
          btn.className = 'download-item-btn download-btn-primary';
          btn.innerHTML = `
            <span>${q.type === 'video' ? '🎬' : '🎵'} ${escapeHtml(q.label)}</span>
            <span class="download-badge">Save to PC ⬇</span>
          `;
          btn.addEventListener('click', () => {
            executeDirectDownload(video.id, q.type, q.quality, video.title, btn);
          });
          downloadFormatsList.appendChild(btn);
        });

        // Section 2: Browser Stream Download
        const heading2 = document.createElement('div');
        heading2.className = 'download-section-title';
        heading2.style.marginTop = '18px';
        heading2.innerHTML = '🌐 Or Download via Browser Window:';
        downloadFormatsList.appendChild(heading2);

        data.qualities.slice(0, 3).forEach(q => {
          const a = document.createElement('a');
          a.className = 'download-item-btn';
          a.href = `/api/stream_download?id=${video.id}&type=${q.type}&quality=${q.quality}&title=${encodeURIComponent(video.title)}`;
          a.target = '_blank';
          a.innerHTML = `
            <span>${q.type === 'video' ? '🎬' : '🎵'} ${escapeHtml(q.label)}</span>
            <span class="download-badge">Browser Stream</span>
          `;
          a.addEventListener('click', () => showToast(`Initiating browser stream for ${q.label}...`));
          downloadFormatsList.appendChild(a);
        });
      })
      .catch(() => {
        downloadFormatsList.innerHTML = '<div style="padding:15px;color:#FF5555;">Could not fetch download options.</div>';
      });
  }

  async function executeDirectDownload(vid, type, quality, title, buttonEl) {
    if (buttonEl) {
      buttonEl.disabled = true;
      buttonEl.dataset.origHtml = buttonEl.innerHTML;
      buttonEl.innerHTML = `<div class="loader-spinner" style="width:16px;height:16px;"></div> <span>Downloading & Multiplexing ${quality}...</span>`;
    }

    showToast(`Started downloading ${type === 'video' ? 'Video' : 'Audio'} in ${quality} to ~/Downloads 💻...`);

    try {
      const res = await fetch(`/api/download_local?id=${vid}&type=${type}&quality=${quality}&title=${encodeURIComponent(title)}`);
      const data = await res.json();

      if (buttonEl && buttonEl.dataset.origHtml) {
        buttonEl.disabled = false;
        buttonEl.innerHTML = buttonEl.dataset.origHtml;
      }

      if (data.status === 'success') {
        showToast(`Downloaded ${data.filename} successfully to ~/Downloads 🎉`);

        const targetContainer = downloadModal.style.display !== 'none' ? downloadFormatsList : inspectResultContainer;
        if (targetContainer) {
          const oldBanner = targetContainer.querySelector('.download-success-banner');
          if (oldBanner) oldBanner.remove();

          const banner = document.createElement('div');
          banner.className = 'download-success-banner';
          banner.innerHTML = `
            <div>✅ <strong>Media stream downloaded successfully!</strong></div>
            <div>File: <strong>${escapeHtml(data.filename)}</strong> (${data.size}) • Quality: <strong>${escapeHtml(data.quality)}</strong></div>
            <div class="download-path-box">${escapeHtml(data.path)}</div>
          `;
          targetContainer.prepend(banner);
        }
      } else {
        showToast('Download error: ' + (data.message || 'Please try another format'));
      }
    } catch (err) {
      if (buttonEl && buttonEl.dataset.origHtml) {
        buttonEl.disabled = false;
        buttonEl.innerHTML = buttonEl.dataset.origHtml;
      }
      showToast('Network error during download. You can use the browser download option.');
    }
  }

  closeDownloadModalBtn.addEventListener('click', () => {
    downloadModal.style.display = 'none';
  });

  downloadModal.addEventListener('click', (e) => {
    if (e.target === downloadModal) downloadModal.style.display = 'none';
  });

  // ==========================================
  // 11. LIBRARY & HISTORY
  // ==========================================
  function addToHistory(video) {
    state.history = state.history.filter(item => item.id !== video.id);
    state.history.unshift(video);
    if (state.history.length > 50) state.history.pop();
    localStorage.setItem('it_history', JSON.stringify(state.history));
  }

  function renderHistoryView() {
    const grid = document.getElementById('historyVideoGrid');
    grid.innerHTML = '';
    if (state.history.length === 0) {
      grid.innerHTML = '<div style="padding:40px;color:var(--text-muted);">Your watch history is empty. Start streaming videos!</div>';
      return;
    }
    renderVideoCards(state.history, grid);
  }

  // ==========================================
  // 12. UTILITIES
  // ==========================================
  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // ==========================================
  // 13. INITIALIZATION
  // ==========================================
  loadHomeVideos(true);
});
