/* JS Document */

$(document).ready(function () {
    "use strict";

    var header = $('.header');
    var menuActive = false;
    var menu = $('.menu');
    var burger = $('.hamburger');
    var backdrop = $('.menu_backdrop');

    setHeader();
    $(window).on('resize', setHeader);
    $(document).on('scroll', setHeader);
    initMenu();

    function setHeader() {
        if ($(window).scrollTop() > 100) {
            header.addClass('scrolled');
        } else {
            header.removeClass('scrolled');
        }
    }

    function initMenu() {
        if (!menu.length || !burger.length) {
            return;
        }

        var closeBtn = $('.menu_close_container');

        function openMenu() {
            menu.addClass('active');
            backdrop.addClass('active');
            $('body').addClass('student-menu-open');
            menuActive = true;
        }

        function closeMenu() {
            menu.removeClass('active');
            backdrop.removeClass('active');
            $('body').removeClass('student-menu-open');
            menuActive = false;
        }

        burger.on('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (menuActive) {
                closeMenu();
            } else {
                openMenu();
            }
        });

        closeBtn.on('click', function (e) {
            e.preventDefault();
            closeMenu();
        });

        backdrop.on('click', closeMenu);

        $('.student-mobile-menu__item, .student-mobile-menu__logout, .student-mobile-menu__login').on('click', function () {
            closeMenu();
        });

        $(document).on('keyup', function (e) {
            if (e.key === 'Escape' && menuActive) {
                closeMenu();
            }
        });
    }
});
