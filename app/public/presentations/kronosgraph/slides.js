const slides = Array.from(document.querySelectorAll('.slide'));
const progressBar = document.getElementById('progressBar');
const slideCounter = document.getElementById('slideCounter');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const dots = document.getElementById('dots');
let index = 0;

function renderDots() {
  dots.innerHTML = '';
  slides.forEach((slide, i) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.setAttribute('aria-label', `跳转到第 ${i + 1} 页：${slide.dataset.title}`);
    button.addEventListener('click', () => goTo(i));
    dots.appendChild(button);
  });
}

function update() {
  slides.forEach((slide, i) => slide.classList.toggle('active', i === index));
  const pct = ((index + 1) / slides.length) * 100;
  progressBar.style.width = `${pct}%`;
  slideCounter.textContent = `${String(index + 1).padStart(2, '0')} / ${String(slides.length).padStart(2, '0')}`;
  Array.from(dots.children).forEach((dot, i) => dot.classList.toggle('active', i === index));
  document.title = `${slides[index].dataset.title} · DragonFlow-KronosGraph`;
}

function goTo(nextIndex) {
  index = Math.max(0, Math.min(slides.length - 1, nextIndex));
  update();
}

prevBtn.addEventListener('click', () => goTo(index - 1));
nextBtn.addEventListener('click', () => goTo(index + 1));
window.addEventListener('keydown', (event) => {
  if (event.key === 'ArrowRight' || event.key === ' ') goTo(index + 1);
  if (event.key === 'ArrowLeft') goTo(index - 1);
  if (event.key === 'Home') goTo(0);
  if (event.key === 'End') goTo(slides.length - 1);
});

renderDots();
update();
