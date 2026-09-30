// Villa Babeh Interactive Calendar, Dynamic Photos, Invoices, Payment Simulation & Web App Logic

let currentYear = new Date().getFullYear();
let currentMonth = new Date().getMonth() + 1; // 1-12
let calendarDates = {};
let appSettings = {};
let facilitiesData = [];
let galleryData = [];
let allBookingsData = [];
let allExpensesData = [];
let activeInvoiceBooking = null;

// Selection State
let checkInDate = null;
let checkOutDate = null;

// Admin State
let isAdmin = false;

// Active photo edit target
let photoEditTarget = null; // { type: 'facility'|'gallery'|'hero', id: number|string }

// Month Names ID
const monthNamesId = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
];

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    await loadSettings();
    await loadFacilities();
    await loadGallery();
    await loadCalendar(currentYear, currentMonth);
    await loadExpenses();
    
    // Check if admin session in localStorage
    if (localStorage.getItem("villa_admin") === "true") {
        enableAdminMode();
    }

    if (window.lucide) {
        lucide.createIcons();
    }
}

// -------------------------------------------------------------
// SETTINGS, FACILITIES & GALLERY LOADING
// -------------------------------------------------------------
async function loadSettings() {
    try {
        const res = await fetch("/api/settings");
        const data = await res.json();
        if (data.status === "success") {
            appSettings = data.settings;
            renderSettingsToUI();
        }
    } catch (e) {
        console.error("Gagal memuat settings:", e);
    }
}

function renderSettingsToUI() {
    document.title = `${appSettings.villa_name || 'Villa Babeh'} - Website Villa & Booking Kalender`;
    
    const navName = document.getElementById("navVillaName");
    if (navName) navName.innerText = appSettings.villa_name || "Villa Babeh";

    const tagline = document.getElementById("heroTagline");
    if (tagline) tagline.innerText = appSettings.tagline || "";

    const desc = document.getElementById("heroDescription");
    if (desc) desc.innerText = appSettings.description || "";

    const navWa = document.getElementById("navWaBtn");
    if (navWa) navWa.href = `https://wa.me/${appSettings.whatsapp}`;

    const footerWaBtn = document.getElementById("footerWaBtn");
    if (footerWaBtn) footerWaBtn.href = `https://wa.me/${appSettings.whatsapp}`;

    const footerWaDisplay = document.getElementById("footerWaDisplay");
    if (footerWaDisplay) footerWaDisplay.innerText = `+${appSettings.whatsapp}`;

    const address = document.getElementById("footerAddress");
    if (address) address.innerText = appSettings.address || "";

    const weekdayPrice = document.getElementById("infoWeekdayPrice");
    if (weekdayPrice) weekdayPrice.innerText = formatRupiah(appSettings.weekday_price || 1500000);

    const weekendPrice = document.getElementById("infoWeekendPrice");
    if (weekendPrice) weekendPrice.innerText = formatRupiah(appSettings.weekend_price || 2200000);

    // Hero background image
    const heroBg = document.getElementById("heroBgImg");
    if (heroBg && appSettings.hero_image) {
        heroBg.style.backgroundImage = `url('${appSettings.hero_image}')`;
    }
    const heroCard = document.getElementById("heroCardImg");
    if (heroCard && appSettings.hero_image) {
        heroCard.src = appSettings.hero_image;
    }

    // Logo render in Navbar
    const navLogoImg = document.getElementById("navLogoImg");
    const navLogoBadge = document.getElementById("navLogoBadge");
    if (appSettings.villa_logo) {
        if (navLogoImg) {
            navLogoImg.src = appSettings.villa_logo;
            navLogoImg.classList.remove("hidden");
        }
        if (navLogoBadge) navLogoBadge.classList.add("hidden");
    } else {
        if (navLogoImg) navLogoImg.classList.add("hidden");
        if (navLogoBadge) navLogoBadge.classList.remove("hidden");
    }
}

async function loadFacilities() {
    try {
        const res = await fetch("/api/facilities");
        const data = await res.json();
        if (data.status === "success") {
            facilitiesData = data.facilities;
            renderFacilitiesUI();
        }
    } catch (e) {
        console.error("Gagal memuat fasilitas:", e);
    }
}

function renderFacilitiesUI() {
    const container = document.getElementById("facilitiesContainer");
    if (!container) return;

    if (facilitiesData.length === 0) {
        container.innerHTML = `<div class="col-span-3 text-center text-gray-400 py-6">Belum ada data fasilitas.</div>`;
        return;
    }

    container.innerHTML = facilitiesData.map(f => {
        const iconName = f.icon || 'star';
        const imgUrl = f.image_url || 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=800&q=80';
        return `
            <div class="bg-gray-50 border border-gray-100 rounded-3xl overflow-hidden hover:shadow-xl hover:border-emerald-200 transition duration-300 space-y-3 flex flex-col group">
                <div class="relative h-48 w-full bg-gray-200 overflow-hidden facility-card-img-container" onclick="handleFacilityPhotoClick(${f.id}, '${imgUrl}')">
                    <img src="${imgUrl}" alt="${f.name}" class="w-full h-full object-cover group-hover:scale-105 transition duration-500">
                    <div class="absolute top-3 left-3 bg-white/90 backdrop-blur-sm text-villa-900 px-2.5 py-1 rounded-full text-xs font-bold shadow flex items-center space-x-1">
                        <i data-lucide="${iconName}" class="w-3.5 h-3.5 inline"></i>
                        <span>${f.category || 'Fasilitas'}</span>
                    </div>

                    <!-- Admin Edit Overlay Badge -->
                    <div class="admin-photo-badge hidden absolute inset-0 bg-slate-900/60 items-center justify-center text-white text-xs font-bold transition">
                        <span class="bg-amber-500 text-slate-950 px-3 py-1.5 rounded-lg shadow flex items-center space-x-1">
                            📷 Klik untuk Ubah Foto
                        </span>
                    </div>
                </div>

                <div class="p-5 pt-0 space-y-2 flex-1 flex flex-col justify-between">
                    <div>
                        <h3 class="font-serif-title font-bold text-lg text-villa-900">${f.name}</h3>
                        <p class="text-xs text-gray-600 leading-relaxed mt-1">${f.description || ''}</p>
                    </div>
                </div>
            </div>
        `;
    }).join("");

    if (window.lucide) lucide.createIcons();
}

async function loadGallery() {
    try {
        const res = await fetch("/api/gallery");
        const data = await res.json();
        if (data.status === "success") {
            galleryData = data.gallery;
            renderGalleryUI();
        }
    } catch (e) {
        console.error("Gagal memuat galeri:", e);
    }
}

function renderGalleryUI() {
    const container = document.getElementById("galleryContainer");
    if (!container) return;

    if (galleryData.length === 0) {
        container.innerHTML = `<div class="col-span-3 text-center text-gray-400 py-6">Belum ada foto galeri.</div>`;
        return;
    }

    container.innerHTML = galleryData.map(g => {
        return `
            <div class="group relative overflow-hidden rounded-3xl shadow-md bg-gray-100 aspect-video gallery-card-img-container cursor-pointer" onclick="handleGalleryPhotoClick(${g.id}, '${g.image_url}', '${g.title}')">
                <img src="${g.image_url}" alt="${g.title}" class="w-full h-full object-cover group-hover:scale-105 transition duration-500">
                <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent flex items-end p-4">
                    <span class="text-white font-bold text-sm truncate">${g.title}</span>
                </div>

                <!-- Admin Edit Overlay Badge -->
                <div class="admin-photo-badge hidden absolute inset-0 bg-slate-900/60 items-center justify-center text-white text-xs font-bold transition">
                    <span class="bg-amber-500 text-slate-950 px-3 py-1.5 rounded-lg shadow flex items-center space-x-1">
                        📷 Klik untuk Ubah Foto
                    </span>
                </div>
            </div>
        `;
    }).join("");
}

// -------------------------------------------------------------
// LOGO & PHOTO EDITING FUNCTIONS
// -------------------------------------------------------------
async function handleLogoUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/upload", { method: "POST", body: formData });
        const data = await res.json();
        if (data.status === "success") {
            document.getElementById("setLogoUrl").value = data.image_url;
            document.getElementById("setLogoPreview").src = data.image_url;
        } else {
            alert(`Gagal mengunggah logo: ${data.message}`);
        }
    } catch (e) {
        alert("Gagal mengunggah logo ke server.");
    }
}

function updateLogoPreviewFromInput() {
    const url = document.getElementById("setLogoUrl").value;
    const preview = document.getElementById("setLogoPreview");
    if (url && preview) preview.src = url;
}

function handleFacilityPhotoClick(id, currentUrl) {
    if (!isAdmin) return;
    openPhotoModal({ type: 'facility', id: id, url: currentUrl });
}

function handleGalleryPhotoClick(id, currentUrl, title) {
    if (!isAdmin) return;
    openPhotoModal({ type: 'gallery', id: id, url: currentUrl, title: title });
}

function handleHeroPhotoClick() {
    if (!isAdmin) return;
    openPhotoModal({ type: 'hero', id: 'hero', url: appSettings.hero_image || '' });
}

function openPhotoModal(target) {
    photoEditTarget = target;
    const modal = document.getElementById("photoEditModal");
    const preview = document.getElementById("photoModalPreview");
    const urlInput = document.getElementById("photoUrlInput");
    const titleGroup = document.getElementById("photoTitleGroup");
    const titleInput = document.getElementById("photoTitleInput");
    const modalTitle = document.getElementById("photoModalTitle");

    preview.src = target.url || "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=800&q=80";
    urlInput.value = target.url || "";
    document.getElementById("photoFileInput").value = "";

    if (target.type === "gallery") {
        modalTitle.innerText = "Ubah Foto Galeri";
        titleGroup.classList.remove("hidden");
        titleInput.value = target.title || "";
    } else if (target.type === "facility") {
        modalTitle.innerText = "Ubah Foto Fasilitas";
        titleGroup.classList.add("hidden");
    } else if (target.type === "hero") {
        modalTitle.innerText = "Ubah Foto Utama Villa (Hero)";
        titleGroup.classList.add("hidden");
    }

    modal.classList.remove("hidden");
}

function closePhotoModal() {
    document.getElementById("photoEditModal").classList.add("hidden");
    photoEditTarget = null;
}

function updatePhotoPreviewFromInput() {
    const url = document.getElementById("photoUrlInput").value;
    const preview = document.getElementById("photoModalPreview");
    if (url) preview.src = url;
}

async function handleLocalFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/upload", { method: "POST", body: formData });
        const data = await res.json();
        if (data.status === "success") {
            document.getElementById("photoUrlInput").value = data.image_url;
            document.getElementById("photoModalPreview").src = data.image_url;
        } else {
            alert(`Gagal mengunggah foto: ${data.message}`);
        }
    } catch (e) {
        alert("Gagal mengunggah foto ke server.");
    }
}

async function savePhotoEdit() {
    if (!photoEditTarget) return;

    const imageUrl = document.getElementById("photoUrlInput").value;
    if (!imageUrl) {
        alert("Mohon pilih berkas atau masukkan URL foto!");
        return;
    }

    try {
        if (photoEditTarget.type === "facility") {
            const fac = facilitiesData.find(f => f.id === photoEditTarget.id);
            if (fac) {
                const res = await fetch("/api/facilities", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        id: fac.id,
                        name: fac.name,
                        description: fac.description,
                        icon: fac.icon,
                        category: fac.category,
                        image_url: imageUrl
                    })
                });
                const data = await res.json();
                if (data.status === "success") {
                    await loadFacilities();
                }
            }
        } else if (photoEditTarget.type === "gallery") {
            const title = document.getElementById("photoTitleInput").value || "Foto Villa";
            const res = await fetch("/api/gallery", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    id: photoEditTarget.id,
                    title: title,
                    image_url: imageUrl
                })
            });
            const data = await res.json();
            if (data.status === "success") {
                await loadGallery();
            }
        } else if (photoEditTarget.type === "hero") {
            const res = await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    admin_pin: appSettings.admin_pin || "1234",
                    hero_image: imageUrl
                })
            });
            const data = await res.json();
            if (data.status === "success") {
                await loadSettings();
            }
        }

        closePhotoModal();
        alert("Foto berhasil diperbarui!");
    } catch (e) {
        alert("Terjadi kesalahan saat menyimpan foto.");
    }
}

// -------------------------------------------------------------
// CALENDAR RENDERING & INTERACTION
// -------------------------------------------------------------
async function loadCalendar(year, month) {
    const title = document.getElementById("calendarMonthTitle");
    if (title) title.innerText = `${monthNamesId[month - 1]} ${year}`;

    const grid = document.getElementById("calendarGrid");
    if (grid) grid.innerHTML = `<div class="col-span-7 py-12 text-center text-gray-400">Memuat kalender...</div>`;

    try {
        const res = await fetch(`/api/calendar?year=${year}&month=${month}`);
        const data = await res.json();
        if (data.status === "success") {
            calendarDates = data.dates;
            renderCalendarGrid(year, month);
        }
    } catch (e) {
        console.error("Gagal memuat kalender:", e);
        if (grid) grid.innerHTML = `<div class="col-span-7 py-12 text-center text-red-500 font-bold">Gagal memuat data kalender.</div>`;
    }
}

function changeMonth(delta) {
    currentMonth += delta;
    if (currentMonth > 12) {
        currentMonth = 1;
        currentYear++;
    } else if (currentMonth < 1) {
        currentMonth = 12;
        currentYear--;
    }
    loadCalendar(currentYear, currentMonth);
}

function resetToToday() {
    const now = new Date();
    currentYear = now.getFullYear();
    currentMonth = now.getMonth() + 1;
    loadCalendar(currentYear, currentMonth);
}

function renderCalendarGrid(year, month) {
    const grid = document.getElementById("calendarGrid");
    if (!grid) return;

    grid.innerHTML = "";

    const firstDayIndex = new Date(year, month - 1, 1).getDay();

    for (let i = 0; i < firstDayIndex; i++) {
        const emptyCell = document.createElement("div");
        emptyCell.className = "calendar-cell empty";
        grid.appendChild(emptyCell);
    }

    const dateKeys = Object.keys(calendarDates).sort();

    dateKeys.forEach(dateStr => {
        const item = calendarDates[dateStr];
        const dayNum = parseInt(dateStr.split("-")[2]);

        const cell = document.createElement("div");
        
        let statusClass = "cell-ready";
        let statusText = "Ready";

        if (item.status === "booked") {
            statusClass = "cell-booked";
            statusText = "Booked";
        } else if (item.status === "maintenance") {
            statusClass = "cell-maintenance";
            statusText = "Maint";
        }

        let isSelected = false;
        let isInRange = false;

        if (checkInDate && checkOutDate) {
            if (dateStr === checkInDate || dateStr === checkOutDate) isSelected = true;
            else if (dateStr > checkInDate && dateStr < checkOutDate) isInRange = true;
        } else if (checkInDate && dateStr === checkInDate) {
            isSelected = true;
        }

        const isHoliday = item.note && (item.note.includes("Libur") || item.note.includes("Tanggal Merah"));
        if (isHoliday && item.status === "ready") {
            statusClass += " border-2 border-red-400 bg-red-50/50";
        }

        if (isSelected) statusClass += " cell-selected";
        else if (isInRange) statusClass += " cell-in-range";

        cell.className = `calendar-cell ${statusClass} animate-fade-in`;
        cell.onclick = () => handleCellClick(dateStr, item);

        cell.innerHTML = `
            <div class="flex justify-between items-start">
                <span class="date-number ${isHoliday ? 'text-red-700 font-extrabold' : ''}">${dayNum}</span>
                <span class="cell-status-badge">${statusText}</span>
            </div>
            ${item.note ? `<div class="text-[9px] truncate font-bold ${isHoliday ? 'text-red-700 bg-red-100 px-1 rounded mt-0.5' : 'opacity-80'}" title="${item.note}">${item.note}</div>` : ''}
            <div class="price-tag ${isHoliday ? 'text-red-700 font-extrabold' : ''}">
                ${formatShortRupiah(item.price)}
            </div>
        `;

        grid.appendChild(cell);
    });
}

function handleCellClick(dateStr, item) {
    if (isAdmin) {
        openSingleDateModal(dateStr, item);
        return;
    }

    if (item.status === "booked" || item.status === "maintenance") {
        alert(`Tanggal ${formatDateIndo(dateStr)} tidak tersedia (${item.status === 'booked' ? 'Sudah Terbooking' : 'Maintenance'}). Mohon pilih tanggal ready!`);
        return;
    }

    if (!checkInDate || (checkInDate && checkOutDate)) {
        checkInDate = dateStr;
        checkOutDate = null;
    } else if (checkInDate && !checkOutDate) {
        if (dateStr <= checkInDate) {
            checkInDate = dateStr;
            checkOutDate = null;
        } else {
            let curr = new Date(checkInDate);
            const target = new Date(dateStr);
            let hasBooked = false;

            while (curr < target) {
                const ds = curr.toISOString().split("T")[0];
                if (calendarDates[ds] && (calendarDates[ds].status === "booked" || calendarDates[ds].status === "maintenance")) {
                    hasBooked = true;
                    break;
                }
                curr.setDate(curr.getDate() + 1);
            }

            if (hasBooked) {
                alert("Rentang tanggal yang Anda pilih melewati tanggal yang sudah terbooking atau maintenance. Silakan pilih rentang lain!");
                return;
            }

            checkOutDate = dateStr;
        }
    }

    updateSelectionUI();
    renderCalendarGrid(currentYear, currentMonth);
}

function updateSelectionUI() {
    const summary = document.getElementById("selectionSummary");
    const btn = document.getElementById("btnSubmitBooking");

    if (!checkInDate) {
        summary.className = "bg-emerald-50/60 border border-emerald-100 rounded-2xl p-4 space-y-3";
        summary.innerHTML = `
            <div class="text-xs text-gray-500 font-medium">Petunjuk:</div>
            <p class="text-sm text-gray-700">
                Klik <strong>Tanggal Check-in</strong> lalu <strong>Tanggal Check-out</strong> pada kalender di samping untuk menghitung harga otomatis.
            </p>
        `;
        if (btn) btn.disabled = true;
        return;
    }

    if (checkInDate && !checkOutDate) {
        summary.className = "bg-amber-50 border border-amber-200 rounded-2xl p-4 space-y-2";
        summary.innerHTML = `
            <div class="text-xs font-bold text-amber-900 uppercase">Check-in Dipilih:</div>
            <div class="font-bold text-base text-amber-950">${formatDateIndo(checkInDate)}</div>
            <p class="text-xs text-amber-800">Sekarang klik <strong>Tanggal Check-out</strong> pada kalender.</p>
        `;
        if (btn) btn.disabled = true;
        return;
    }

    const nights = calculateNights(checkInDate, checkOutDate);
    const totalPrice = calculateTotalPriceRange(checkInDate, checkOutDate);
    const defaultDp = Math.round(totalPrice / 2);

    const displayPriceElem = document.getElementById("displayTotalPrice");
    if (displayPriceElem) displayPriceElem.value = formatRupiah(totalPrice);

    const totalDpElem = document.getElementById("totalDp");
    if (totalDpElem && !totalDpElem.value) totalDpElem.value = defaultDp;

    summary.className = "bg-indigo-50 border border-indigo-200 rounded-2xl p-4 space-y-3 animate-fade-in";
    summary.innerHTML = `
        <div class="flex justify-between items-center text-xs font-bold text-indigo-900 uppercase">
            <span>Pilihan Tanggal</span>
            <span class="bg-indigo-600 text-white px-2 py-0.5 rounded-full text-[10px]">${nights} Malam</span>
        </div>
        <div class="text-xs space-y-1 text-gray-700">
            <div>Check-in: <strong class="text-indigo-950">${formatDateIndo(checkInDate)}</strong> (14:00 WIB)</div>
            <div>Check-out: <strong class="text-indigo-950">${formatDateIndo(checkOutDate)}</strong> (12:00 WIB)</div>
        </div>
        <div class="pt-2 border-t border-indigo-100 flex justify-between items-center">
            <span class="text-xs font-bold text-gray-600">Estimasi Biaya:</span>
            <span class="font-serif-title font-bold text-xl text-emerald-700">${formatRupiah(totalPrice)}</span>
        </div>
    `;

    if (btn) btn.disabled = false;
}

function resetDateSelection() {
    checkInDate = null;
    checkOutDate = null;
    const displayPriceElem = document.getElementById("displayTotalPrice");
    if (displayPriceElem) displayPriceElem.value = "";
    const totalDpElem = document.getElementById("totalDp");
    if (totalDpElem) totalDpElem.value = "";
    updateSelectionUI();
    renderCalendarGrid(currentYear, currentMonth);
}

function calculateNights(startStr, endStr) {
    const s = new Date(startStr);
    const e = new Date(endStr);
    const diffTime = Math.abs(e - s);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

function calculateTotalPriceRange(startStr, endStr) {
    let total = 0;
    let curr = new Date(startStr);
    const end = new Date(endStr);

    while (curr < end) {
        const ds = curr.toISOString().split("T")[0];
        if (calendarDates[ds]) {
            total += calendarDates[ds].price;
        } else {
            const isWeekend = curr.getDay() === 5 || curr.getDay() === 6 || curr.getDay() === 0;
            total += isWeekend ? parseInt(appSettings.weekend_price || 2200000) : parseInt(appSettings.weekday_price || 1500000);
        }
        curr.setDate(curr.getDate() + 1);
    }
    return total;
}

// -------------------------------------------------------------
// BOOKING SUBMISSION VIA WHATSAPP (Format Pemesanan Official)
// -------------------------------------------------------------
async function submitBooking(event) {
    event.preventDefault();
    if (!checkInDate || !checkOutDate) {
        alert("Mohon pilih Tanggal Check-in dan Tanggal Check-out pada kalender ketersediaan!");
        return;
    }

    const guestName = document.getElementById("guestName").value;
    const transferNameElem = document.getElementById("transferName");
    const transferName = transferNameElem && transferNameElem.value ? transferNameElem.value : guestName;

    const guestPhone = document.getElementById("guestPhone").value;
    const totalGuestsElem = document.getElementById("totalGuests");
    const totalGuests = totalGuestsElem && totalGuestsElem.value ? totalGuestsElem.value : "10 Orang";

    const guestIgElem = document.getElementById("guestIg");
    const guestIg = guestIgElem && guestIgElem.value ? guestIgElem.value : "-";

    const nights = calculateNights(checkInDate, checkOutDate);
    const totalPrice = calculateTotalPriceRange(checkInDate, checkOutDate);
    const defaultDp = Math.round(totalPrice / 2);

    const totalDpElem = document.getElementById("totalDp");
    const totalDpVal = totalDpElem && totalDpElem.value ? parseInt(totalDpElem.value) : defaultDp;

    const datesText = `${formatDateIndo(checkInDate)} s/d ${formatDateIndo(checkOutDate)} (${nights} Malam)`;

    try {
        await fetch("/api/bookings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                guest_name: guestName,
                guest_phone: guestPhone,
                check_in: checkInDate,
                check_out: checkOutDate,
                notes: `Pentransfer: ${transferName} | Tamu: ${totalGuests} | IG: ${guestIg} | DP: ${formatRupiah(totalDpVal)}`
            })
        });
    } catch (e) {}

    // Exact Format Pemesanan requested by user
    const message = `Format pemesanan 

Nama pemesan : ${guestName}
Nama pentransfer : ${transferName}
Hp : ${guestPhone}
Tgl menginap : ${datesText}
Total tamu : ${totalGuests}
Total harga : ${formatRupiah(totalPrice)}
Total DP : ${formatRupiah(totalDpVal)}
Nama instagram : ${guestIg}`;

    const waNumber = appSettings.whatsapp || "6281234567890";
    const encodedMessage = encodeURIComponent(message);
    window.open(`https://wa.me/${waNumber}?text=${encodedMessage}`, "_blank");

    resetDateSelection();
    document.getElementById("bookingForm").reset();
    loadCalendar(currentYear, currentMonth);
}

// -------------------------------------------------------------
// ADMIN FUNCTIONALITIES
// -------------------------------------------------------------
function promptAdminLogin() {
    const pin = prompt("Masukkan PIN Admin Pengelola (Default: 1234):");
    if (!pin) return;

    const expectedPin = appSettings.admin_pin || "1234";
    if (pin === expectedPin) {
        enableAdminMode();
        alert("Login Admin Berhasil! Klik foto fasilitas atau tanggal mana saja untuk langsung mengubahnya.");
    } else {
        alert("PIN Admin salah!");
    }
}

function enableAdminMode() {
    isAdmin = true;
    localStorage.setItem("villa_admin", "true");

    const banner = document.getElementById("adminModeBanner");
    if (banner) banner.classList.remove("hidden");

    document.body.classList.add("admin-mode-active");
    renderCalendarGrid(currentYear, currentMonth);
    renderFacilitiesUI();
    renderGalleryUI();
}

function logoutAdmin() {
    isAdmin = false;
    localStorage.removeItem("villa_admin");

    const banner = document.getElementById("adminModeBanner");
    if (banner) banner.classList.add("hidden");

    document.body.classList.remove("admin-mode-active");
    renderCalendarGrid(currentYear, currentMonth);
    renderFacilitiesUI();
    renderGalleryUI();
    alert("Anda telah keluar dari mode admin.");
}

function openSingleDateModal(dateStr, item) {
    document.getElementById("modalDateTitle").innerText = `Atur Tanggal: ${formatDateIndo(dateStr)}`;
    document.getElementById("editTargetDate").value = dateStr;
    document.getElementById("editStatusSelect").value = item.status || "ready";
    document.getElementById("editPriceInput").value = item.price || "";
    document.getElementById("editNoteInput").value = item.note || "";

    document.getElementById("singleDateModal").classList.remove("hidden");
}

function closeSingleDateModal() {
    document.getElementById("singleDateModal").classList.add("hidden");
}

async function saveSingleDateEdit() {
    const dateStr = document.getElementById("editTargetDate").value;
    const status = document.getElementById("editStatusSelect").value;
    const price = document.getElementById("editPriceInput").value;
    const note = document.getElementById("editNoteInput").value;

    try {
        const res = await fetch("/api/calendar/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                start_date: dateStr,
                end_date: dateStr,
                status: status,
                price: price,
                note: note
            })
        });
        const data = await res.json();
        if (data.status === "success") {
            closeSingleDateModal();
            loadCalendar(currentYear, currentMonth);
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert("Gagal mengupdate tanggal.");
    }
}

function openAdminModal() {
    document.getElementById("adminDashboardModal").classList.remove("hidden");
    document.getElementById("setVillaName").value = appSettings.villa_name || "";
    document.getElementById("setTagline").value = appSettings.tagline || "";
    document.getElementById("setDescription").value = appSettings.description || "";
    document.getElementById("setWhatsapp").value = appSettings.whatsapp || "";
    document.getElementById("setWeekdayPrice").value = appSettings.weekday_price || 1500000;
    document.getElementById("setWeekendPrice").value = appSettings.weekend_price || 2200000;
    document.getElementById("setAddress").value = appSettings.address || "";
    
    // Logo setting
    document.getElementById("setLogoUrl").value = appSettings.villa_logo || "";
    const preview = document.getElementById("setLogoPreview");
    if (preview) preview.src = appSettings.villa_logo || "";

    const todayStr = new Date().toISOString().split("T")[0];
    document.getElementById("batchStartDate").value = todayStr;
    document.getElementById("batchEndDate").value = todayStr;

    renderAdminGalleryList();
}

function closeAdminModal() {
    document.getElementById("adminDashboardModal").classList.add("hidden");
}

function switchAdminTab(tabName) {
    const allTabs = ["dashboard", "dates", "bookings", "reports", "gallery", "facilities", "settings"];

    // 1. Hide/Show Tab Contents
    allTabs.forEach(t => {
        const contentId = `tabContent${t.charAt(0).toUpperCase() + t.slice(1)}`;
        const contentElem = document.getElementById(contentId);
        if (contentElem) {
            if (t === tabName) {
                contentElem.classList.remove("hidden");
            } else {
                contentElem.classList.add("hidden");
            }
        }

        // Old modal tabs (index.html)
        const oldBtnId = `tabBtn${t.charAt(0).toUpperCase() + t.slice(1)}`;
        const oldBtnElem = document.getElementById(oldBtnId);
        if (oldBtnElem) {
            if (t === tabName) {
                oldBtnElem.className = "pb-3 border-b-2 border-villa-900 text-villa-900 font-bold transition flex items-center space-x-1 whitespace-nowrap";
            } else {
                oldBtnElem.className = "pb-3 border-b-2 border-transparent hover:text-villa-900 transition flex items-center space-x-1 whitespace-nowrap";
            }
        }
    });

    // 2. Update Desktop Sidebar Active State (admin.html)
    const navMap = {
        'dashboard': 'navDash',
        'dates': 'navDates',
        'bookings': 'navBookings',
        'reports': 'navReports',
        'gallery': 'navGallery',
        'facilities': 'navFacilities',
        'settings': 'navSettings'
    };

    Object.keys(navMap).forEach(key => {
        const navId = navMap[key];
        const navElem = document.getElementById(navId);
        if (navElem) {
            if (key === tabName) {
                navElem.className = "w-full text-left px-4 py-3 rounded-2xl bg-teal-800 text-amber-400 font-bold flex items-center space-x-3 transition shadow-sm";
            } else {
                navElem.className = "w-full text-left px-4 py-3 rounded-2xl text-teal-100 hover:bg-teal-800 transition flex items-center space-x-3 font-semibold";
            }
        }
    });

    // 3. Update Mobile Bottom Nav Active State (admin.html)
    const mNavMap = {
        'dashboard': 'mNavDash',
        'dates': 'mNavDates',
        'bookings': 'mNavBookings',
        'reports': 'mNavReports',
        'gallery': 'mNavGallery',
        'facilities': 'mNavFacilities',
        'settings': 'mNavSettings'
    };

    Object.keys(mNavMap).forEach(key => {
        const mNavId = mNavMap[key];
        const mNavElem = document.getElementById(mNavId);
        if (mNavElem) {
            if (key === tabName) {
                mNavElem.className = "flex flex-col items-center space-y-0.5 text-[10px] font-bold text-amber-400 min-w-[48px]";
            } else {
                mNavElem.className = "flex flex-col items-center space-y-0.5 text-[10px] font-bold text-teal-200 hover:text-white min-w-[48px]";
            }
        }
    });

    // 4. Trigger Data Reload / Render for Target Tab
    if (tabName === "dashboard") {
        updateDashboardKPIs();
    } else if (tabName === "dates") {
        loadCalendar(currentYear, currentMonth);
    } else if (tabName === "bookings") {
        loadAdminBookings();
    } else if (tabName === "reports") {
        loadAdminBookings().then(() => {
            loadExpenses().then(() => {
                renderReportSummaryList();
            });
        });
    } else if (tabName === "gallery") {
        renderAdminGalleryList();
    } else if (tabName === "facilities") {
        renderAdminFacilities();
    } else if (tabName === "settings") {
        populateAdminSettingsForm();
    }

    if (window.lucide) {
        lucide.createIcons();
    }
}

async function syncNationalHolidays() {
    if (!confirm(`Sinkronkan Tanggal Merah & Hari Libur Nasional Indonesia tahun ${currentYear} ke kalender villa?`)) return;

    try {
        const res = await fetch("/api/calendar/sync_holidays", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ year: currentYear })
        });
        const data = await res.json();
        if (data.status === "success") {
            alert(data.message);
            await loadCalendar(currentYear, currentMonth);
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert("Gagal menyingkronkan hari libur nasional.");
    }
}

// -------------------------------------------------------------
// EXPENSES & CASHFLOW MANAGEMENT
// -------------------------------------------------------------
async function loadExpenses() {
    try {
        const res = await fetch("/api/expenses");
        const data = await res.json();
        if (data.status === "success") {
            allExpensesData = data.expenses || [];
            renderExpensesUI();
            updateDashboardKPIs();
        }
    } catch (e) {
        console.error("Gagal memuat data pengeluaran:", e);
    }
}

function renderExpensesUI() {
    const tbody = document.getElementById("expensesTableBody");
    const monthFilterElem = document.getElementById("filterBookingMonth");
    const monthFilter = monthFilterElem ? monthFilterElem.value : 'all';

    let filtered = (allExpensesData || []).filter(e => {
        if (monthFilter === "all") return true;
        return e.expense_date.startsWith(monthFilter);
    });

    const totalExpElem = document.getElementById("reportTotalExpensesBadge");
    const totalExp = filtered.reduce((acc, curr) => acc + (curr.amount || 0), 0);
    if (totalExpElem) totalExpElem.innerText = `Total Pengeluaran: ${formatRupiah(totalExp)}`;

    if (!tbody) return;

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-gray-400 text-xs">Belum ada catatan pengeluaran untuk periode ini.</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(e => `
        <tr class="hover:bg-gray-50 text-xs">
            <td class="p-3 font-semibold text-gray-800">${e.title}</td>
            <td class="p-3"><span class="bg-gray-100 text-gray-700 font-bold px-2 py-0.5 rounded text-[10px]">${e.category || 'Operasional'}</span></td>
            <td class="p-3 font-bold text-red-600">${formatRupiah(e.amount)}</td>
            <td class="p-3 text-gray-600">${formatDateIndo(e.expense_date)}</td>
            <td class="p-3 text-gray-500 italic">${e.notes || '-'}</td>
            <td class="p-3 text-center">
                <button onclick="deleteExpenseItem(${e.id})" class="text-red-500 hover:text-red-700 font-bold text-xs bg-red-50 hover:bg-red-100 px-2 py-1 rounded-lg transition">
                    🗑️ Hapus
                </button>
            </td>
        </tr>
    `).join("");
}

async function submitAddExpense(event) {
    event.preventDefault();
    const title = document.getElementById("expTitle").value;
    const category = document.getElementById("expCategory").value;
    const amount = document.getElementById("expAmount").value;
    const expenseDate = document.getElementById("expDate").value;
    const notes = document.getElementById("expNotes").value;

    try {
        const res = await fetch("/api/expenses", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: title,
                category: category,
                amount: amount,
                expense_date: expenseDate,
                notes: notes
            })
        });

        const data = await res.json();
        if (data.status === "success") {
            alert(data.message);
            document.getElementById("expTitle").value = "";
            document.getElementById("expAmount").value = "";
            document.getElementById("expNotes").value = "";
            await loadExpenses();
            if (typeof renderReportSummaryList === "function") renderReportSummaryList();
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert("Gagal mencatat pengeluaran.");
    }
}

async function deleteExpenseItem(id) {
    if (!confirm("Hapus catatan pengeluaran ini?")) return;
    try {
        const res = await fetch(`/api/expenses?id=${id}`, { method: "DELETE" });
        const data = await res.json();
        if (data.status === "success") {
            await loadExpenses();
            if (typeof renderReportSummaryList === "function") renderReportSummaryList();
        }
    } catch (e) {
        alert("Gagal menghapus pengeluaran.");
    }
}

function populateAdminSettingsForm() {
    if (!appSettings) return;
    const fields = {
        "setVillaName": appSettings.villa_name || "",
        "setTagline": appSettings.tagline || "",
        "setDescription": appSettings.description || "",
        "setWhatsapp": appSettings.whatsapp || "",
        "setWeekdayPrice": appSettings.weekday_price || 1500000,
        "setWeekendPrice": appSettings.weekend_price || 2200000,
        "setAddress": appSettings.address || "",
        "setLogoUrl": appSettings.villa_logo || ""
    };
    for (const [id, val] of Object.entries(fields)) {
        const elem = document.getElementById(id);
        if (elem) elem.value = val;
    }
    const preview = document.getElementById("setLogoPreview");
    if (preview && appSettings.villa_logo) preview.src = appSettings.villa_logo;
}

function renderReportSummaryList() {
    const container = document.getElementById("reportSummaryList");
    if (!container) return;

    const monthFilterElem = document.getElementById("filterBookingMonth");
    const monthFilter = monthFilterElem ? monthFilterElem.value : 'all';
    
    let filtered = (allBookingsData || []).filter(b => {
        if (monthFilter === "all") return true;
        return b.check_in.startsWith(monthFilter);
    });

    let filteredExpenses = (allExpensesData || []).filter(e => {
        if (monthFilter === "all") return true;
        return e.expense_date.startsWith(monthFilter);
    });

    const totalOmset = filtered.reduce((acc, b) => acc + (b.total_price || 0), 0);
    const totalKas = filtered.reduce((acc, b) => acc + (b.total_paid || 0), 0);
    const totalPiutang = filtered.reduce((acc, b) => acc + (b.remaining_balance || 0), 0);
    const totalExp = filteredExpenses.reduce((acc, e) => acc + (e.amount || 0), 0);
    const netProfit = totalKas - totalExp;

    container.innerHTML = `
        <table class="w-full text-left text-xs">
            <thead class="bg-teal-900 text-white font-bold uppercase text-[10px]">
                <tr>
                    <th class="p-3">Inv No</th>
                    <th class="p-3">Nama Pemesan</th>
                    <th class="p-3">Check-In</th>
                    <th class="p-3">Check-Out</th>
                    <th class="p-3 text-right">Biaya Sewa</th>
                    <th class="p-3 text-right">Kas Masuk (DP/Lunas)</th>
                    <th class="p-3 text-right">Sisa Tagihan</th>
                    <th class="p-3 text-center">Status</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
                ${filtered.length === 0 ? `<tr><td colspan="8" class="p-4 text-center text-gray-400">Belum ada transaksi untuk periode ini.</td></tr>` : 
                filtered.map(b => {
                    const padId = String(b.id).padStart(3, '0');
                    const invNo = `INV/VB/${(b.check_in || '2026-09').replace('-', '').slice(0, 6)}/${padId}`;
                    return `
                        <tr class="hover:bg-gray-50">
                            <td class="p-3 font-semibold text-gray-700">${invNo}</td>
                            <td class="p-3 font-bold">${b.guest_name}</td>
                            <td class="p-3">${b.check_in}</td>
                            <td class="p-3">${b.check_out}</td>
                            <td class="p-3 text-right font-bold text-gray-900">${formatRupiah(b.total_price)}</td>
                            <td class="p-3 text-right font-bold text-emerald-700">${formatRupiah(b.total_paid || 0)}</td>
                            <td class="p-3 text-right font-bold text-amber-600">${formatRupiah(b.remaining_balance || 0)}</td>
                            <td class="p-3 text-center">
                                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold ${b.payment_status === 'LUNAS' ? 'bg-emerald-100 text-emerald-800' : (b.payment_status === 'DP TERBAYAR' ? 'bg-amber-100 text-amber-900' : 'bg-red-100 text-red-800')}">
                                    ${b.payment_status}
                                </span>
                            </td>
                        </tr>
                    `;
                }).join("")}
            </tbody>
            <tfoot class="bg-teal-50 font-bold border-t border-teal-200">
                <tr>
                    <td colspan="4" class="p-3 text-right uppercase text-gray-600 text-[11px]">Total Perhitungan:</td>
                    <td class="p-3 text-right text-gray-900 font-bold">${formatRupiah(totalOmset)}</td>
                    <td class="p-3 text-right text-emerald-700 font-bold">${formatRupiah(totalKas)}</td>
                    <td class="p-3 text-right text-amber-600 font-bold">${formatRupiah(totalPiutang)}</td>
                    <td></td>
                </tr>
                <tr class="bg-indigo-50 border-t border-indigo-200 text-indigo-900 text-xs">
                    <td colspan="4" class="p-3 text-right uppercase font-extrabold">Ringkasan Arus Kas & Keuntungan Bersih:</td>
                    <td colspan="2" class="p-3 text-right font-bold text-red-600">Beban Pengeluaran: ${formatRupiah(totalExp)}</td>
                    <td colspan="2" class="p-3 text-right font-extrabold text-indigo-950 font-serif-title text-sm">KEUNTUNGAN BERSIH: ${formatRupiah(netProfit)}</td>
                </tr>
            </tfoot>
        </table>
    `;
}

function renderAdminGalleryList() {
    const container = document.getElementById("adminGalleryList");
    if (!container) return;

    if (galleryData.length === 0) {
        container.innerHTML = `<div class="col-span-3 text-center text-gray-400 py-6">Belum ada foto.</div>`;
        return;
    }

    container.innerHTML = galleryData.map(g => `
        <div class="bg-gray-50 rounded-2xl overflow-hidden border border-gray-200 p-2 space-y-2">
            <img src="${g.image_url}" class="w-full h-24 object-cover rounded-xl">
            <div class="text-xs font-bold truncate">${g.title}</div>
            <div class="flex space-x-1">
                <button onclick="handleGalleryPhotoClick(${g.id}, '${g.image_url}', '${g.title}')" class="flex-1 bg-amber-100 hover:bg-amber-200 text-amber-900 font-bold py-1 rounded text-[10px]">
                    Ubah Foto
                </button>
                <button onclick="deleteGalleryPhoto(${g.id})" class="bg-red-100 hover:bg-red-200 text-red-700 font-bold px-2 py-1 rounded text-[10px]">
                    Hapus
                </button>
            </div>
        </div>
    `).join("");
}

function openAddNewGalleryModal() {
    openPhotoModal({ type: 'gallery', id: null, url: '', title: '' });
}

async function deleteGalleryPhoto(id) {
    if (!confirm("Hapus foto ini dari galeri?")) return;
    try {
        const res = await fetch(`/api/gallery?id=${id}`, { method: "DELETE" });
        const data = await res.json();
        if (data.status === "success") {
            await loadGallery();
            renderAdminGalleryList();
        }
    } catch (e) {
        alert("Gagal menghapus foto galeri.");
    }
}

async function submitBatchDateUpdate(event) {
    event.preventDefault();
    const startDate = document.getElementById("batchStartDate").value;
    const endDate = document.getElementById("batchEndDate").value;
    const status = document.getElementById("batchStatus").value;
    const price = document.getElementById("batchPrice").value;
    const note = document.getElementById("batchNote").value;

    try {
        const res = await fetch("/api/calendar/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate,
                status: status,
                price: price,
                note: note
            })
        });

        const data = await res.json();
        if (data.status === "success") {
            alert(data.message);
            loadCalendar(currentYear, currentMonth);
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert("Gagal memperbarui jadwal massal.");
    }
}

async function submitGeneralSettings(event) {
    event.preventDefault();
    const villaName = document.getElementById("setVillaName").value;
    const tagline = document.getElementById("setTagline").value;
    const description = document.getElementById("setDescription").value;
    const whatsapp = document.getElementById("setWhatsapp").value;
    const adminPin = appSettings.admin_pin || "1234";
    const newAdminPin = document.getElementById("setAdminPin").value;
    const weekdayPrice = document.getElementById("setWeekdayPrice").value;
    const weekendPrice = document.getElementById("setWeekendPrice").value;
    const address = document.getElementById("setAddress").value;
    const villaLogo = document.getElementById("setLogoUrl").value;

    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                admin_pin: adminPin,
                new_admin_pin: newAdminPin || undefined,
                villa_name: villaName,
                tagline: tagline,
                description: description,
                whatsapp: whatsapp,
                weekday_price: weekdayPrice,
                weekend_price: weekendPrice,
                address: address,
                villa_logo: villaLogo
            })
        });

        const data = await res.json();
        if (data.status === "success") {
            alert(data.message);
            await loadSettings();
            loadCalendar(currentYear, currentMonth);
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert("Gagal menyimpan pengaturan.");
    }
}

// -------------------------------------------------------------
// BOOKING LIST, MONTH FILTER, PAYMENTS & INVOICE MANAGEMENT
// -------------------------------------------------------------
async function loadAdminBookings() {
    const tbody = document.getElementById("bookingsTableBody");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-gray-400">Memuat data...</td></tr>`;

    try {
        const res = await fetch("/api/bookings");
        const data = await res.json();
        if (data.status === "success") {
            allBookingsData = data.bookings || [];
            filterAdminBookings();
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-red-500">Gagal memuat booking.</td></tr>`;
    }
}

function filterAdminBookings() {
    const tbody = document.getElementById("bookingsTableBody");
    const monthFilterElem = document.getElementById("filterBookingMonth");
    const monthFilter = monthFilterElem ? monthFilterElem.value : "all";
    const sortOrderElem = document.getElementById("sortBookingOrder");
    const sortOrder = sortOrderElem ? sortOrderElem.value : "desc";
    const statsBadge = document.getElementById("bookingStatsBadge");

    // Sync Dashboard KPIs and Report Summary List if on screen
    if (typeof updateDashboardKPIs === "function") updateDashboardKPIs();
    if (typeof renderReportSummaryList === "function") renderReportSummaryList();

    if (!tbody) return;

    if (!allBookingsData || allBookingsData.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-gray-400">Belum ada riwayat booking.</td></tr>`;
        if (statsBadge) statsBadge.innerText = "Total: 0 Booking";
        return;
    }

    let filtered = allBookingsData.filter(b => {
        if (monthFilter === "all") return true;
        return b.check_in.startsWith(monthFilter);
    });

    filtered.sort((a, b) => {
        if (sortOrder === "asc") {
            return a.check_in.localeCompare(b.check_in);
        } else {
            return b.check_in.localeCompare(a.check_in);
        }
    });

    const totalRev = filtered.reduce((acc, curr) => acc + (curr.total_price || 0), 0);
    if (statsBadge) {
        statsBadge.innerText = `Total: ${filtered.length} Booking | Biaya: ${formatRupiah(totalRev)}`;
    }

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-gray-400">Tidak ada booking untuk bulan ini.</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(b => {
        let statusBadgeHTML = '';
        if (b.payment_status === "LUNAS") {
            statusBadgeHTML = `<span class="bg-emerald-100 text-emerald-800 font-bold px-2.5 py-1 rounded-full text-[10px] border border-emerald-300">🟢 LUNAS</span>`;
        } else if (b.payment_status === "DP TERBAYAR") {
            statusBadgeHTML = `
                <div class="space-y-0.5">
                    <span class="bg-amber-100 text-amber-900 font-bold px-2 py-0.5 rounded-full text-[10px] border border-amber-300 inline-block">🟡 DP TERBAYAR</span>
                    <span class="text-[10px] text-gray-500 block">Sisa: <strong class="text-red-600">${formatRupiah(b.remaining_balance)}</strong></span>
                </div>
            `;
        } else {
            statusBadgeHTML = `<span class="bg-red-100 text-red-700 font-bold px-2.5 py-1 rounded-full text-[10px] border border-red-300">🔴 BELUM BAYAR</span>`;
        }

        return `
            <tr class="hover:bg-gray-50 transition">
                <td class="p-3 font-bold">
                    <div class="flex items-center justify-between">
                        <span>${b.guest_name}</span>
                        <button onclick="openInvoiceModal(${b.id})" title="Lihat/Cetak Invoice" class="ml-2 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-lg text-[10px] font-bold shadow-sm transition flex items-center space-x-1">
                            <span>🧾 Invoice</span>
                        </button>
                    </div>
                </td>
                <td class="p-3"><a href="https://wa.me/${b.guest_phone}" target="_blank" class="text-emerald-600 underline font-medium">${b.guest_phone}</a></td>
                <td class="p-3 font-semibold text-gray-800">${b.check_in}</td>
                <td class="p-3 font-semibold text-gray-800">${b.check_out}</td>
                <td class="p-3 font-bold text-gray-900">${formatRupiah(b.total_price)}</td>
                <td class="p-3">${statusBadgeHTML}</td>
                <td class="p-3 text-center">
                    <div class="flex items-center justify-center space-x-1">
                        <button onclick="openPaymentModal(${b.id})" title="Simulasi & Catat Pembayaran DP/Pelunasan" class="bg-emerald-600 hover:bg-emerald-700 text-white px-2.5 py-1 rounded-lg text-[11px] font-bold shadow transition flex items-center space-x-1">
                            <span>💳 +Bayar</span>
                        </button>
                        <button onclick="openInvoiceModal(${b.id})" class="bg-blue-100 hover:bg-blue-200 text-blue-800 px-2 py-1 rounded-lg text-[11px] font-bold transition">
                            🧾 Invoice
                        </button>
                        <button onclick="deleteBooking(${b.id})" class="bg-red-100 hover:bg-red-200 text-red-700 px-2 py-1 rounded-lg text-[11px] font-bold transition">
                            Hapus
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

// -------------------------------------------------------------
// PAYMENT RECORDING & SIMULATION MODAL
// -------------------------------------------------------------
async function openPaymentModal(bookingId) {
    const booking = allBookingsData.find(b => b.id === bookingId);
    if (!booking) return;

    document.getElementById("payModalBookingId").value = booking.id;
    document.getElementById("payModalGuestName").innerText = booking.guest_name;
    document.getElementById("payModalTotalPrice").innerText = formatRupiah(booking.total_price);
    
    // Set default payment date to today
    document.getElementById("payInputDate").value = new Date().toISOString().split("T")[0];

    // Determine default payment stage name
    const payCount = (booking.payments || []).length;
    const nameSelect = document.getElementById("payInputName");
    if (nameSelect) {
        if (payCount === 0) nameSelect.value = "DP (Pembayaran 1)";
        else if (payCount === 1) nameSelect.value = "Pembayaran Ke-2";
        else if (payCount === 2) nameSelect.value = "Pembayaran Ke-3";
        else nameSelect.value = "Pelunasan";
    }

    await refreshPaymentModalData(booking.id);
    document.getElementById("paymentRecordModal").classList.remove("hidden");
}

function closePaymentModal() {
    document.getElementById("paymentRecordModal").classList.add("hidden");
}

async function refreshPaymentModalData(bookingId) {
    try {
        const res = await fetch(`/api/payments?booking_id=${bookingId}`);
        const data = await res.json();
        if (data.status === "success") {
            const totalPaid = data.total_paid;
            const remaining = data.remaining_balance;
            const payments = data.payments;

            document.getElementById("payModalTotalPaid").innerText = formatRupiah(totalPaid);
            document.getElementById("payModalRemaining").innerText = formatRupiah(remaining);
            document.getElementById("payInputAmount").value = remaining > 0 ? remaining : "";

            const historyList = document.getElementById("payModalHistoryList");
            if (payments.length === 0) {
                historyList.innerHTML = `<div class="p-3 text-center text-gray-400 bg-gray-50 rounded-xl text-xs">Belum ada pembayaran dicatat (Belum DP).</div>`;
            } else {
                historyList.innerHTML = payments.map(p => `
                    <div class="flex justify-between items-center bg-gray-50 p-2.5 rounded-xl border border-gray-200 text-xs">
                        <div>
                            <strong class="text-gray-900 font-bold">${p.payment_name}</strong>
                            <span class="text-gray-500 text-[10px] block">${formatDateIndo(p.payment_date)}</span>
                        </div>
                        <div class="flex items-center space-x-2">
                            <strong class="text-emerald-700 font-bold">${formatRupiah(p.amount)}</strong>
                            <button onclick="deletePayment(${p.id}, ${bookingId})" class="text-red-500 hover:text-red-700 font-bold text-[10px] bg-red-50 hover:bg-red-100 p-1 rounded">
                                ❌
                            </button>
                        </div>
                    </div>
                `).join("");
            }
        }
    } catch (e) {
        console.error("Gagal memuat rincian pembayaran:", e);
    }
}

async function submitNewPayment(event) {
    event.preventDefault();
    const bookingId = document.getElementById("payModalBookingId").value;
    const paymentName = document.getElementById("payInputName").value;
    const amount = document.getElementById("payInputAmount").value;
    const paymentDate = document.getElementById("payInputDate").value;

    try {
        const res = await fetch("/api/payments", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                booking_id: bookingId,
                payment_name: paymentName,
                amount: amount,
                payment_date: paymentDate
            })
        });

        const data = await res.json();
        if (data.status === "success") {
            alert(data.message);
            await refreshPaymentModalData(bookingId);
            await loadAdminBookings();
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert("Gagal menginput pembayaran.");
    }
}

async function deletePayment(paymentId, bookingId) {
    if (!confirm("Hapus catatan pembayaran ini?")) return;
    try {
        const res = await fetch(`/api/payments?id=${paymentId}`, { method: "DELETE" });
        const data = await res.json();
        if (data.status === "success") {
            await refreshPaymentModalData(bookingId);
            await loadAdminBookings();
        }
    } catch (e) {
        alert("Gagal menghapus catatan pembayaran.");
    }
}

// -------------------------------------------------------------
// INVOICE GENERATION WITH LOGO & PAYMENT BREAKDOWN
// -------------------------------------------------------------
function openInvoiceModal(bookingId) {
    const booking = allBookingsData.find(b => b.id === bookingId);
    if (!booking) return;

    activeInvoiceBooking = booking;

    const padId = String(booking.id).padStart(3, '0');
    const createdYearMonth = (booking.check_in || "2026-09").replace("-", "").slice(0, 6);
    const invNo = `INV/VB/${createdYearMonth}/${padId}`;

    const nights = calculateNights(booking.check_in, booking.check_out);

    // Villa Details & Logo
    document.getElementById("invNumber").innerText = invNo;
    document.getElementById("invCreatedDate").innerText = `Tanggal: ${formatDateIndo(booking.created_at ? booking.created_at.split(" ")[0] : booking.check_in)}`;
    document.getElementById("invVillaName").innerText = appSettings.villa_name || "Villa Babeh";
    document.getElementById("invAddress").innerText = appSettings.address || "Jl. Raya Puncak No. 88, Bogor";
    document.getElementById("invWa").innerText = `+${appSettings.whatsapp || '6281234567890'}`;

    // Logo Render in Invoice
    const invLogoImg = document.getElementById("invLogoImg");
    const invLogoBadge = document.getElementById("invLogoBadge");
    if (appSettings.villa_logo) {
        if (invLogoImg) {
            invLogoImg.src = appSettings.villa_logo;
            invLogoImg.classList.remove("hidden");
        }
        if (invLogoBadge) invLogoBadge.classList.add("hidden");
    } else {
        if (invLogoImg) invLogoImg.classList.add("hidden");
        if (invLogoBadge) invLogoBadge.classList.remove("hidden");
    }

    // Guest Details
    document.getElementById("invGuestName").innerText = booking.guest_name;
    document.getElementById("invGuestPhone").innerText = booking.guest_phone;
    
    const notesElem = document.getElementById("invGuestNotes");
    if (notesElem) notesElem.innerText = booking.notes || "-";

    document.getElementById("invCheckIn").innerText = formatDateIndo(booking.check_in);
    document.getElementById("invCheckOut").innerText = formatDateIndo(booking.check_out);
    document.getElementById("invNights").innerText = `${nights} Malam`;
    
    document.getElementById("invPeriodText").innerText = `Periode: ${formatDateIndo(booking.check_in)} s/d ${formatDateIndo(booking.check_out)}`;
    document.getElementById("invTableNights").innerText = `${nights} Malam`;
    document.getElementById("invTableTotal").innerText = formatRupiah(booking.total_price);
    document.getElementById("invGrandTotal").innerText = formatRupiah(booking.total_price);

    // Payment Simulation & Breakdown Calculation
    const payments = booking.payments || [];
    const totalPaid = booking.total_paid || 0;
    const remaining = booking.remaining_balance || 0;

    const breakdownContainer = document.getElementById("invPaymentsBreakdown");
    if (payments.length === 0) {
        breakdownContainer.innerHTML = `
            <div class="flex justify-between items-center text-gray-500 italic">
                <span>• Belum ada pembayaran masuk (DP 0%)</span>
                <span>Rp 0</span>
            </div>
        `;
    } else {
        breakdownContainer.innerHTML = payments.map(p => `
            <div class="flex justify-between items-center text-gray-800 font-medium">
                <span>• ${p.payment_name} (${formatDateIndo(p.payment_date)}):</span>
                <strong class="text-emerald-800">${formatRupiah(p.amount)}</strong>
            </div>
        `).join("");
    }

    document.getElementById("invTotalPaid").innerText = formatRupiah(totalPaid);
    document.getElementById("invRemainingBalance").innerText = formatRupiah(remaining);

    // Status Stamp Badge in Invoice
    const statusBadge = document.getElementById("invStatusBadge");
    const statusTag = document.getElementById("invPaymentStatusTag");
    
    let statusText = "LUNAS / TERKONFIRMASI";
    let statusClass = "bg-emerald-100 text-emerald-800 border-emerald-300";
    let tagClass = "bg-emerald-600 text-white";

    if (remaining <= 0 && totalPaid > 0) {
        statusText = "LUNAS / TERKONFIRMASI";
        statusClass = "bg-emerald-100 text-emerald-800 border-emerald-300";
        tagClass = "bg-emerald-600 text-white";
    } else if (totalPaid > 0) {
        statusText = `DP TERBAYAR (SISA: ${formatRupiah(remaining)})`;
        statusClass = "bg-amber-100 text-amber-900 border-amber-300";
        tagClass = "bg-amber-600 text-white";
    } else {
        statusText = "BELUM BAYAR (MENUNGGU DP)";
        statusClass = "bg-red-100 text-red-800 border-red-300";
        tagClass = "bg-red-600 text-white";
    }

    if (statusBadge) {
        statusBadge.innerText = statusText;
        statusBadge.className = `text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full border ${statusClass}`;
    }
    if (statusTag) {
        statusTag.innerText = remaining <= 0 && totalPaid > 0 ? "LUNAS" : (totalPaid > 0 ? "DP TERBAYAR" : "BELUM BAYAR");
        statusTag.className = `text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full ${tagClass}`;
    }

    document.getElementById("invoiceModal").classList.remove("hidden");
    if (window.lucide) lucide.createIcons();
}

function closeInvoiceModal() {
    document.getElementById("invoiceModal").classList.add("hidden");
    activeInvoiceBooking = null;
}

function sendInvoiceToWa() {
    if (!activeInvoiceBooking) return;
    const b = activeInvoiceBooking;
    const padId = String(b.id).padStart(3, '0');
    const createdYearMonth = (b.check_in || "2026-09").replace("-", "").slice(0, 6);
    const invNo = `INV/VB/${createdYearMonth}/${padId}`;
    const nights = calculateNights(b.check_in, b.check_out);

    const totalPaid = b.total_paid || 0;
    const remaining = b.remaining_balance || 0;
    let statusStr = remaining <= 0 && totalPaid > 0 ? "LUNAS" : (totalPaid > 0 ? `DP TERBAYAR (Sisa: ${formatRupiah(remaining)})` : "BELUM BAYAR");

    let paymentsStr = "";
    if (b.payments && b.payments.length > 0) {
        paymentsStr = b.payments.map(p => `  • ${p.payment_name}: ${formatRupiah(p.amount)} (${formatDateIndo(p.payment_date)})`).join("\n");
    } else {
        paymentsStr = "  • Belum ada DP masuk.";
    }

    const message = `🧾 *INVOICE RESERVASI ${appSettings.villa_name || 'VILLA BABEH'}*
----------------------------------------
No. Invoice: *${invNo}*
Status: *${statusStr}*

👤 *Detail Pemesan:*
• Nama: ${b.guest_name}
• WA: ${b.guest_phone}

📅 *Rincian Reservasi:*
• Check-In: ${formatDateIndo(b.check_in)} (14:00 WIB)
• Check-Out: ${formatDateIndo(b.check_out)} (12:00 WIB)
• Durasi: ${nights} Malam
• Total Biaya Sewa: *${formatRupiah(b.total_price)}*

💳 *Simulasi Pembayaran Masuk:*
${paymentsStr}
----------------------------------------
• *Total Masuk:* ${formatRupiah(totalPaid)}
• *SISA TAGIHAN:* ${formatRupiah(remaining)}

Terima kasih atas kepercayaan Anda menginap di ${appSettings.villa_name || 'Villa Babeh'}! Sampai jumpa di lokasi. 🙏`;

    const encoded = encodeURIComponent(message);
    window.open(`https://wa.me/${b.guest_phone}?text=${encoded}`, "_blank");
}

async function deleteBooking(id) {
    if (!confirm("Batalkan booking ini dan bebaskan tanggal kembali ke Ready?")) return;

    try {
        const res = await fetch(`/api/bookings?id=${id}`, { method: "DELETE" });
        const data = await res.json();
        if (data.status === "success") {
            alert("Booking berhasil dibatalkan.");
            loadAdminBookings();
            loadCalendar(currentYear, currentMonth);
        }
    } catch (e) {
        alert("Gagal membatalkan booking.");
    }
}

function renderAdminFacilities() {
    const container = document.getElementById("adminFacilitiesList");
    if (!container) return;

    container.innerHTML = facilitiesData.map(f => `
        <div class="flex justify-between items-center bg-gray-50 p-3 rounded-xl border border-gray-200">
            <div class="flex items-center space-x-3">
                <img src="${f.image_url || 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=800&q=80'}" class="w-12 h-12 object-cover rounded-lg">
                <div>
                    <strong class="text-sm font-bold text-gray-800">${f.name}</strong>
                    <span class="text-xs text-gray-500 block">${f.description || ''}</span>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                <button onclick="handleFacilityPhotoClick(${f.id}, '${f.image_url || ''}')" class="bg-amber-100 text-amber-900 hover:bg-amber-200 text-xs px-2.5 py-1 rounded font-bold">
                    📷 Ubah Foto
                </button>
                <button onclick="deleteFacility(${f.id})" class="bg-red-100 text-red-700 hover:bg-red-200 text-xs px-2.5 py-1 rounded font-bold">
                    Hapus
                </button>
            </div>
        </div>
    `).join("");
}

async function submitAddFacility(event) {
    event.preventDefault();
    const name = document.getElementById("facName").value;
    const desc = document.getElementById("facDesc").value;
    const cat = document.getElementById("facCategory").value;
    const img = document.getElementById("facImg").value;

    try {
        const res = await fetch("/api/facilities", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: name, description: desc, category: cat, image_url: img })
        });
        const data = await res.json();
        if (data.status === "success") {
            await loadFacilities();
            renderAdminFacilities();
            document.getElementById("facName").value = "";
            document.getElementById("facDesc").value = "";
            document.getElementById("facCategory").value = "";
            document.getElementById("facImg").value = "";
        }
    } catch (e) {
        alert("Gagal menambah fasilitas.");
    }
}

async function deleteFacility(id) {
    if (!confirm("Hapus fasilitas ini?")) return;
    try {
        const res = await fetch(`/api/facilities?id=${id}`, { method: "DELETE" });
        const data = await res.json();
        if (data.status === "success") {
            await loadFacilities();
            renderAdminFacilities();
        }
    } catch (e) {
        alert("Gagal menghapus fasilitas.");
    }
}

// -------------------------------------------------------------
// HELPER FORMATTING FUNCTIONS
// -------------------------------------------------------------
function formatRupiah(amount) {
    return new Intl.NumberFormat("id-ID", {
        style: "currency",
        currency: "IDR",
        maximumFractionDigits: 0
    }).format(amount);
}

function formatShortRupiah(amount) {
    if (!amount) return "";
    const val = parseInt(amount);
    if (val >= 1000000) {
        const million = (val / 1000000).toFixed(val % 1000000 === 0 ? 0 : 1);
        return `Rp ${million}M`;
    } else if (val >= 1000) {
        return `Rp ${(val / 1000).toFixed(0)}rb`;
    }
    return `Rp ${val}`;
}

function formatDateIndo(dateStr) {
    if (!dateStr) return "";
    const parts = dateStr.split("-");
    if (parts.length < 3) return dateStr;
    const d = parseInt(parts[2]);
    const m = parseInt(parts[1]) - 1;
    const y = parts[0];
    return `${d} ${monthNamesId[m]} ${y}`;
}

function toggleMobileMenu() {
    const drawer = document.getElementById("mobileNavDrawer");
    if (drawer) {
        drawer.classList.toggle("hidden");
    }
}

async function submitGeneralSettings(event) {
    event.preventDefault();
    const nameElem = document.getElementById("setVillaName");
    const taglineElem = document.getElementById("setTagline");
    const descElem = document.getElementById("setDescription");
    const waElem = document.getElementById("setWhatsapp");
    const pinElem = document.getElementById("setAdminPin");
    const weekdayElem = document.getElementById("setWeekdayPrice");
    const weekendElem = document.getElementById("setWeekendPrice");
    const addressElem = document.getElementById("setAddress");
    const logoElem = document.getElementById("setLogoUrl");

    const payload = {
        villa_name: nameElem ? nameElem.value : (appSettings.villa_name || "Villa Babeh"),
        tagline: taglineElem ? taglineElem.value : (appSettings.tagline || ""),
        description: descElem ? descElem.value : (appSettings.description || ""),
        whatsapp: waElem ? waElem.value : (appSettings.whatsapp || ""),
        weekday_price: weekdayElem ? weekdayElem.value : (appSettings.weekday_price || "1500000"),
        weekend_price: weekendElem ? weekendElem.value : (appSettings.weekend_price || "2200000"),
        address: addressElem ? addressElem.value : (appSettings.address || ""),
        villa_logo: logoElem ? logoElem.value : (appSettings.villa_logo || "/static/images/logo.jpg")
    };

    if (pinElem && pinElem.value && pinElem.value.trim() !== "") {
        payload.admin_pin = pinElem.value.trim();
    }

    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === "success") {
            alert("Pengaturan Villa berhasil disimpan!");
            await loadSettings();
        } else {
            alert("Gagal menyimpan pengaturan: " + data.message);
        }
    } catch (e) {
        alert("Gagal menghubungi server.");
    }
}

async function submitChangeAdminPin(event) {
    event.preventDefault();
    const currentPin = document.getElementById("currentPinInput").value;
    const newPin = document.getElementById("newPinInput").value;
    const confirmNewPin = document.getElementById("confirmNewPinInput").value;

    const expectedPin = appSettings.admin_pin || "1234";

    if (currentPin !== expectedPin) {
        alert("PIN Admin saat ini (lama) yang Anda masukkan SALAH!");
        return;
    }

    if (!newPin || newPin.length < 4) {
        alert("PIN baru minimal harus 4 karakter/angka!");
        return;
    }

    if (newPin !== confirmNewPin) {
        alert("Konfirmasi PIN baru tidak cocok! Mohon periksa kembali.");
        return;
    }

    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ admin_pin: newPin })
        });
        const data = await res.json();
        if (data.status === "success") {
            appSettings.admin_pin = newPin;
            alert("🔒 PIN Admin berhasil diubah! Gunakan PIN baru ini untuk login berikutnya.");
            document.getElementById("currentPinInput").value = "";
            document.getElementById("newPinInput").value = "";
            document.getElementById("confirmNewPinInput").value = "";
        } else {
            alert("Gagal memperbarui PIN: " + data.message);
        }
    } catch (e) {
        alert("Terjadi kesalahan koneksi saat mengubah PIN.");
    }
}

