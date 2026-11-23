<?php
// The language pack adds "pixels" even though phpBB already supplies that unit.
$path = '/var/www/html/language/pt_br/ucp.php';
$contents = file_get_contents($path);
if ($contents === false)
{
    throw new RuntimeException('Portuguese language file is missing.');
}

$replacements = [
    'Dimensões máximas: largura %1$s pixels, altura %2$s pixels, tamanho %3$.2f KiB.'
        => 'Dimensões máximas: largura %1$s, altura %2$s, tamanho %3$.2f KiB.',
    'Dimensões máximas; largura %1$s pixels, altura %2$s. pixels'
        => 'Dimensões máximas: largura %1$s, altura %2$s.',
];
foreach ($replacements as $old => $new)
{
    if (substr_count($contents, $old) !== 1)
    {
        throw new RuntimeException('Unexpected Portuguese avatar translation.');
    }
    $contents = str_replace($old, $new, $contents);
}

if (file_put_contents($path, $contents) === false)
{
    throw new RuntimeException('Cannot patch Portuguese avatar translation.');
}

$path = '/var/www/html/language/pt_br/common.php';
$contents = file_get_contents($path);
if ($contents === false)
{
    throw new RuntimeException('Portuguese common language file is missing.');
}
$old = 'O avatar enviado possui %5$s pixels de largura e %6$s pixels de altura. O avatar deve possuir no mínimo %1$s pixels de largura, %2$s pixels altura e no máximo %3$s pixels de largura e %4$s pixels de altura.';
$new = 'O avatar enviado possui %5$s de largura e %6$s de altura. O avatar deve possuir no mínimo %1$s de largura, %2$s de altura e no máximo %3$s de largura e %4$s de altura.';
if (substr_count($contents, $old) !== 1)
{
    throw new RuntimeException('Unexpected Portuguese avatar size translation.');
}
if (file_put_contents($path, str_replace($old, $new, $contents)) === false)
{
    throw new RuntimeException('Cannot patch Portuguese avatar size translation.');
}
