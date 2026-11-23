FROM php:8.3-apache-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends git unzip libicu-dev libjpeg62-turbo-dev libpng-dev libwebp-dev libavif-dev libzip-dev \
    && docker-php-ext-configure gd --with-jpeg --with-webp --with-avif \
    && docker-php-ext-install gd intl mysqli pdo_mysql zip \
    && a2enmod rewrite \
    && rm -rf /var/lib/apt/lists/*

COPY --from=composer:2 /usr/bin/composer /usr/local/bin/composer

RUN git clone --depth 1 --branch release-3.3.19 https://github.com/phpbb/phpbb.git /tmp/phpbb-source \
    && cp -a /tmp/phpbb-source/phpBB/. /var/www/html/ \
    && cd /var/www/html \
    && composer install --no-dev --no-interaction --prefer-dist --no-progress \
    && rm -rf /tmp/phpbb-source /var/www/html/install \
    && chown -R www-data:www-data /var/www/html

COPY patches/avatar-reencode.patch /tmp/avatar-reencode.patch
RUN cd /var/www/html \
    && git apply --check /tmp/avatar-reencode.patch \
    && git apply /tmp/avatar-reencode.patch \
    && rm /tmp/avatar-reencode.patch

COPY patches/avatar-thumbnail.patch /tmp/avatar-thumbnail.patch
RUN cd /var/www/html \
    && git apply --check /tmp/avatar-thumbnail.patch \
    && git apply /tmp/avatar-thumbnail.patch \
    && rm /tmp/avatar-thumbnail.patch

COPY vendor/brazilian_portuguese_3_3_19.zip /tmp/phpbb-pt-br.zip
COPY patches/pt-br-avatar.php /tmp/pt-br-avatar.php
RUN echo '378abe4e6055a5bcfb6fec45a4b0a530cb760da0418a611426f32adc859b57ba  /tmp/phpbb-pt-br.zip' | sha256sum -c - \
    && unzip -q /tmp/phpbb-pt-br.zip -d /tmp/phpbb-pt-br \
    && cp -a /tmp/phpbb-pt-br/brazilian_portuguese_3_3_19/language/pt_br /var/www/html/language/ \
    && cp -a /tmp/phpbb-pt-br/brazilian_portuguese_3_3_19/styles/prosilver/theme/pt_br /var/www/html/styles/prosilver/theme/ \
    && php /tmp/pt-br-avatar.php \
    && rm -rf /tmp/phpbb-pt-br /tmp/phpbb-pt-br.zip /tmp/pt-br-avatar.php

COPY ext/dndtools/brand /var/www/html/ext/dndtools/brand
COPY ext/dndtools/discussions /var/www/html/ext/dndtools/discussions
COPY vendor/ajax_litechat_2_1_0.zip /tmp/ajax-litechat.zip
COPY patches/litechat-base-path.patch /tmp/litechat-base-path.patch
RUN echo '22e4af7c297b256a6caf56127b18203be5b5e03f944d87b4efa0c52e75182503  /tmp/ajax-litechat.zip' | sha256sum -c - \
    && unzip -q /tmp/ajax-litechat.zip -d /var/www/html/ext \
    && cd /var/www/html && git apply --check /tmp/litechat-base-path.patch \
    && git apply /tmp/litechat-base-path.patch \
    && rm /tmp/ajax-litechat.zip
COPY chat-pt-br /var/www/html/ext/stoker/chat/language/pt_br
COPY install-language.php /usr/local/bin/dndtools-install-language.php
COPY configure-chat.php /usr/local/bin/dndtools-configure-chat.php
COPY publish-rules.php /usr/local/bin/dndtools-publish-rules.php
COPY repair-topic-authors.php /usr/local/bin/dndtools-repair-topic-authors.php
COPY entrypoint.sh /usr/local/bin/dndtools-forum-entrypoint
RUN chmod 755 /usr/local/bin/dndtools-forum-entrypoint

RUN printf '%s\n' '<Directory /var/www/html>' 'AllowOverride All' 'Require all granted' '</Directory>' > /etc/apache2/conf-available/phpbb-local.conf \
    && a2enconf phpbb-local

ENTRYPOINT ["/usr/local/bin/dndtools-forum-entrypoint"]
CMD ["apache2-foreground"]
