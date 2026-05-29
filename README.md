cd caldwell-cosmetics
.\venv\Scripts\Activate.ps1

or

.\start-dev.ps1

How to run dev settings:

$env:DJANGO_SETTINGS_MODULE="config.settings.dev"
python manage.py runserver

DJANGO_SETTINGS_MODULE=config.settings.prod

Template Structure:

templates/
├─ base/
│ ├─ base.html <-- main template
│ ├─ \_navbar.html <-- navbar only
│ ├─ \_footer.html <-- footer only
│ ├─ \_modals.html <-- all modal popups
├─ core/
│ └─ home.html
│ └─ cookies.html
│ └─ dashboard.html
│ └─ privacy.html
│ └─ terms.html
├─ treatments/
├─ bookings/
├─ accounts/

Static Structure:

static/
├─ css/
│ ├─ style.css
│ ├─ navbar.css
│ ├─ footer.css
│ └─ bootstrap.min.css
├─ js/
│ ├─ script.js
│ ├─ calendar.js
│ └─ bootstrap.bundle.min.js
├─ images/
├─ favicon/

<!-- Gallery Carousel -->

    <section class="section section--gallery">
        <div class="container">
            <div class="gallery-carousel" id="galleryCarousel">
                <div class="gallery-carousel__inner">

                    <!-- Slide 1 -->
                    <div class="gallery-carousel__item gallery-carousel__item--active">
                        <div class="gallery-grid">
                            <div class="gallery-grid__item">
                                <video
                                    src="https://res.cloudinary.com/ddj2rpxcb/video/upload/v1755382637/M5hmG5Xv_a0ivsm.mp4"
                                    class="gallery-grid__media"
                                    autoplay
                                    muted
                                    loop
                                    playsinline
                                    aria-label="Treatment demonstration video"
                                >
                                    Your browser does not support the video tag.
                                </video>
                            </div>

                            <div class="gallery-grid__item">
                                <img
                                    src="https://res.cloudinary.com/ddj2rpxcb/image/upload/v1750199188/M339WHoP_h1foad.jpg"
                                    class="gallery-grid__media"
                                    alt="Client wearing protective goggles during treatment"
                                    loading="lazy"
                                >
                            </div>

                            <div class="gallery-grid__item">
                                <img
                                    src="https://res.cloudinary.com/ddj2rpxcb/image/upload/v1750199217/PfUXDT_K_h3fxzz.jpg"
                                    class="gallery-grid__media"
                                    alt="Professional skin consultation session"
                                    loading="lazy"
                                >
                            </div>

                            <div class="gallery-grid__item">
                                <video
                                    src="https://res.cloudinary.com/ddj2rpxcb/video/upload/v1755382637/Tglo7yac_y9xhic.mp4"
                                    class="gallery-grid__media"
                                    autoplay
                                    muted
                                    loop
                                    playsinline
                                    aria-label="Skincare treatment demonstration"
                                >
                                    Your browser does not support the video tag.
                                </video>
                            </div>
                        </div>
                    </div>

                    <!-- Slide 2 -->
                    <div class="gallery-carousel__item">
                        <div class="gallery-grid">
                            <div class="gallery-grid__item">
                                <video
                                    src="https://res.cloudinary.com/ddj2rpxcb/video/upload/v1755382639/hJesY0oz_dckp8q.mp4"
                                    class="gallery-grid__media"
                                    autoplay
                                    muted
                                    loop
                                    playsinline
                                    aria-label="Treatment procedure video"
                                >
                                    Your browser does not support the video tag.
                                </video>
                            </div>

                            <div class="gallery-grid__item">
                                <img
                                    src="https://res.cloudinary.com/ddj2rpxcb/image/upload/v1750199969/OVgW8loX_jh7dia.jpg"
                                    class="gallery-grid__media"
                                    alt="Treatment room with Where The Magic Happens signage"
                                    loading="lazy"
                                >
                            </div>

                            <div class="gallery-grid__item">
                                <img
                                    src="https://res.cloudinary.com/ddj2rpxcb/image/upload/v1750199297/WlsG5qsb_zpn2pl.jpg"
                                    class="gallery-grid__media"
                                    alt="Clinic interior featuring motivational signage"
                                    loading="lazy"
                                >
                            </div>

                            <div class="gallery-grid__item">
                                <video
                                    src="https://res.cloudinary.com/ddj2rpxcb/video/upload/v1755382637/HQZkuraG_akptes.mp4"
                                    class="gallery-grid__media"
                                    autoplay
                                    muted
                                    loop
                                    playsinline
                                    aria-label="Advanced treatment technique video"
                                >
                                    Your browser does not support the video tag.
                                </video>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Carousel Progress Indicators (optional) -->
                <div class="gallery-carousel__indicators">
                    <button class="gallery-carousel__indicator gallery-carousel__indicator--active" aria-label="Go to slide 1"></button>
                    <button class="gallery-carousel__indicator" aria-label="Go to slide 2"></button>
                </div>
            </div>
        </div>
    </section>
