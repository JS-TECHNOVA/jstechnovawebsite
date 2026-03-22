const mobileMenuOpenBtn = document.getElementById("mobileMenuOpenBtn");
const mobileMenuCloseBtn = document.getElementById("mobileMenuCloseBtn");
const mobileMenuOverlay = document.getElementById("mobileMenuOverlay");
const mobileMenuPanel = document.getElementById("mobileMenuPanel");
const mobileMenuBackdrop = document.getElementById("mobileMenuBackdrop");
const mobileMenuLinks = Array.from(
	document.querySelectorAll("[data-mobile-menu-link]"),
);

if (
	mobileMenuOpenBtn &&
	mobileMenuCloseBtn &&
	mobileMenuOverlay &&
	mobileMenuPanel &&
	mobileMenuBackdrop
) {
	const openMobileMenu = () => {
		mobileMenuOverlay.classList.remove("pointer-events-none", "opacity-0");
		mobileMenuOverlay.classList.add("opacity-100");
		requestAnimationFrame(() => {
			mobileMenuPanel.classList.remove("translate-x-full");
		});
		document.body.classList.add("overflow-hidden");
	};

	const closeMobileMenu = () => {
		mobileMenuPanel.classList.add("translate-x-full");
		mobileMenuOverlay.classList.remove("opacity-100");
		mobileMenuOverlay.classList.add("opacity-0");
		setTimeout(() => {
			mobileMenuOverlay.classList.add("pointer-events-none");
		}, 300);
		document.body.classList.remove("overflow-hidden");
	};

	mobileMenuOpenBtn.addEventListener("click", openMobileMenu);
	mobileMenuCloseBtn.addEventListener("click", closeMobileMenu);
	mobileMenuBackdrop.addEventListener("click", closeMobileMenu);

	mobileMenuLinks.forEach((link) => {
		link.addEventListener("click", closeMobileMenu);
	});

	document.addEventListener("keydown", (event) => {
		if (event.key === "Escape") closeMobileMenu();
	});
}

if (window.AOS) {
	AOS.init({
		duration: 850,
		easing: "ease-out-cubic",
		once: false,
		mirror: true,
		offset: 70,
	});
}
