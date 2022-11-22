$(document).ready(function() {
      $(document).on('click', '.toggle-menu', function() {
        var menu = document.getElementById('mobile-menu');
        function toggleMenu() {
            menu.classList.toggle('hidden');
            menu.classList.toggle('w-full');
            menu.classList.toggle('h-screen');
        }
        toggleMenu()
      });
})
