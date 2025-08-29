// Carousel
const carousel = document.querySelector(".carousel");
const cards = document.querySelectorAll(".event-card");

let currentIndex = 0;
const visibleCards = 3;

function nextSlide() {
  if (currentIndex < cards.length - visibleCards) {
    currentIndex++;
    updateCarousel();
  }
}

function prevSlide() {
  if (currentIndex > 0) {
    currentIndex--;
    updateCarousel();
  }
}

function updateCarousel() {
  const cardWidth = cards[0].offsetWidth + 20; // include gap
  carousel.style.transform = `translateX(-${currentIndex * cardWidth}px)`;
}

// Auto-slide every 5 seconds
setInterval(() => {
  if (currentIndex < cards.length - visibleCards) {
    nextSlide();
  } else {
    currentIndex = 0;
    updateCarousel();
  }
}, 5000);

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener("click", function(e) {
    e.preventDefault();
    document.querySelector(this.getAttribute("href")).scrollIntoView({
      behavior: "smooth"
    });
  });
});
