<?php

/**
 * Brazilian Portuguese help for the Markdown extension.
 * @license GPL-2.0-only
 */

if (!defined('IN_PHPBB'))
{
	exit;
}

if (empty($lang) || !is_array($lang))
{
	$lang = [];
}

$lang = array_merge($lang, [
	'MARKDOWN_GUIDE' => 'Guia de Markdown',

	'HELP_MARKDOWN_BLOCK_INTRO' => 'Introdução',
	'HELP_MARKDOWN_INTRO_MARKDOWN_QUESTION' => 'O que é Markdown?',
	'HELP_MARKDOWN_INTRO_MARKDOWN_ANSWER' => 'Markdown é uma linguagem leve de marcação para formatar texto. Você escreve usando caracteres comuns, sem precisar de um editor especial, e o resultado aparece formatado na página. É possível usar Markdown junto com BBCode ou no lugar dele.',

	'HELP_MARKDOWN_BLOCK_TEXT' => 'Formatação de texto',
	'HELP_MARKDOWN_TEXT_BOLD_QUESTION' => 'Como escrever em negrito?',
	'HELP_MARKDOWN_TEXT_BOLD_ANSWER' => 'Coloque o texto entre dois <code>**</code> ou dois <code>__</code>. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">**Olá**</code></pre> ou <pre class="markdown-code"><code class="markdown" data-lang="markdown">__Olá__</code></pre> aparece como:<br><br><strong>Olá</strong>',
	'HELP_MARKDOWN_TEXT_ITALIC_QUESTION' => 'Como escrever em itálico?',
	'HELP_MARKDOWN_TEXT_ITALIC_ANSWER' => 'Coloque o texto entre <code>*</code> ou entre <code>_</code>. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">*Ótimo!*</code></pre> ou <pre class="markdown-code"><code class="markdown" data-lang="markdown">_Ótimo!_</code></pre> aparece como:<br><br><em>Ótimo!</em>',
	'HELP_MARKDOWN_TEXT_STRIKETHROUGH_QUESTION' => 'Como riscar um texto?',
	'HELP_MARKDOWN_TEXT_STRIKETHROUGH_ANSWER' => 'Coloque o texto entre <code>~~</code>. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">~~Bom dia~~</code></pre> aparece como:<br><br><del>Bom dia</del>',
	'HELP_MARKDOWN_TEXT_SUBSCRIPT_QUESTION' => 'Como escrever em subscrito?',
	'HELP_MARKDOWN_TEXT_SUBSCRIPT_ANSWER' => 'Coloque o texto entre <code>~</code>. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">H~2~O</code></pre> aparece como:<br><br>H<sub>2</sub>O',
	'HELP_MARKDOWN_TEXT_SUPERSCRIPT_QUESTION' => 'Como escrever em sobrescrito?',
	'HELP_MARKDOWN_TEXT_SUPERSCRIPT_ANSWER' => 'Adicione <code>^</code> antes do texto. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">2^n</code></pre> aparece como:<br><br>2<sup>n</sup>',
	'HELP_MARKDOWN_TEXT_HEADER_QUESTION' => 'Como criar títulos?',
	'HELP_MARKDOWN_TEXT_HEADER_ANSWER' => 'Comece a linha com um a seis sinais <code>#</code> seguidos de um espaço. Quanto mais sinais, menor o título. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown"># Título 1<br>## Título 2<br>### Título 3<br>#### Título 4<br>##### Título 5<br>###### Título 6</code></pre> aparece como:<br><br><h1 class="markdown">Título 1</h1><h2 class="markdown">Título 2</h2><h3 class="markdown">Título 3</h3><h4 class="markdown">Título 4</h4><h5 class="markdown">Título 5</h5><h6 class="markdown">Título 6</h6>',

	'HELP_MARKDOWN_BLOCK_CODE' => 'Citações e código',
	'HELP_MARKDOWN_QUOTE_QUESTION' => 'Como citar um texto?',
	'HELP_MARKDOWN_QUOTE_ANSWER' => 'Comece a linha com <code>&gt;</code>, seguido opcionalmente de um espaço. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">&gt; Texto citado</code></pre> aparece como:<blockquote class="uncited"><div><p>Texto citado</p></div></blockquote>',
	'HELP_MARKDOWN_CODE_QUESTION' => 'Como mostrar um bloco de código?',
	'HELP_MARKDOWN_CODE_ANSWER' => 'Coloque o código entre duas linhas com <code>```</code> ou <code>~~~</code>. Você também pode recuar cada linha com quatro espaços. Para indicar a linguagem, escreva seu nome após os três acentos graves:<pre class="markdown-code"><code class="markdown" data-lang="markdown">```ruby<br>puts "Olá, #{user}!"<br>```</code></pre> aparece como:<div class="codebox"><p>Código:</p><pre><code>puts "Olá, #{user}!"</code></pre></div>',
	'HELP_MARKDOWN_CODE_INLINE_QUESTION' => 'Como mostrar código dentro de uma frase?',
	'HELP_MARKDOWN_CODE_INLINE_ANSWER' => 'Coloque o trecho entre <code>`</code> ou <code>``</code>. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">Tag `&lt;div&gt;`</code></pre> ou <pre class="markdown-code"><code class="markdown" data-lang="markdown">Tag ``&lt;div&gt;``</code></pre> aparece como:<br><br>Tag <code>&lt;div&gt;</code>',

	'HELP_MARKDOWN_BLOCK_TABLE' => 'Tabelas',
	'HELP_MARKDOWN_TABLE_QUESTION' => 'Como criar uma tabela?',
	'HELP_MARKDOWN_TABLE_ANSWER' => 'Separe as colunas com <code>|</code>. Na linha seguinte, use <code>-</code> para separar o cabeçalho e <code>:</code> para alinhar cada coluna à esquerda, ao centro ou à direita. As linhas seguintes viram o conteúdo da tabela. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">| Esquerda | Centro | Direita |<br>|:---------|:------:|--------:|<br>|    x     |    x   |    x    |</code></pre> ou <pre class="markdown-code"><code class="markdown" data-lang="markdown">Esquerda|Centro|Direita<br>:-|:-:|-:<br>x|x|x</code></pre> aparece como:<br><br><table class="markdown"><thead><tr><th style="text-align:left">Esquerda</th><th style="text-align:center">Centro</th><th style="text-align:right">Direita</th></tr></thead><tbody><tr><td style="text-align:left">x</td><td style="text-align:center">x</td><td style="text-align:right">x</td></tr></tbody></table>',

	'HELP_MARKDOWN_BLOCK_SPOILER' => 'Spoilers',
	'HELP_MARKDOWN_BLOCK_SPOILER_QUESTION' => 'Como criar um bloco de spoiler?',
	'HELP_MARKDOWN_BLOCK_SPOILER_ANSWER' => 'Comece a linha com <code>&gt;!</code>, seguido opcionalmente de um espaço. Nas linhas seguintes, use <code>&gt;</code>. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">&gt;! Texto oculto<br>&gt; Outra linha</code></pre> aparece como:<br><br><details class="spoiler markdown"><p>Texto oculto<br>Outra linha</p></details>',
	'HELP_MARKDOWN_INLINE_SPOILER_QUESTION' => 'Como ocultar parte de uma frase?',
	'HELP_MARKDOWN_INLINE_SPOILER_ANSWER' => 'Coloque o texto entre <code>&gt;!</code> e <code>!&lt;</code>, como no Reddit, ou entre <code>||</code>, como no Discord. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">Um &gt;!spoiler!&lt; na frase.<br>Outro ||spoiler|| na frase.</code></pre> A parte oculta fica visível ao ser revelada.',

	'HELP_MARKDOWN_BLOCK_LIST' => 'Listas',
	'HELP_MARKDOWN_UNORDERED_LIST_QUESTION' => 'Como criar uma lista com marcadores?',
	'HELP_MARKDOWN_UNORDERED_LIST_ANSWER' => 'Comece cada item com <code>*</code>, <code>-</code> ou <code>+</code>, seguido de um espaço. Para criar um subitem, acrescente quatro espaços ou um tab no início da linha. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">- Item<br>    - Subitem<br>- Item</code></pre> aparece como:<br><br><ul class="markdown"><li>Item<ul class="markdown"><li>Subitem</li></ul></li><li>Item</li></ul>',
	'HELP_MARKDOWN_ORDERED_LIST_QUESTION' => 'Como criar uma lista numerada?',
	'HELP_MARKDOWN_ORDERED_LIST_ANSWER' => 'Comece cada item com um número, um ponto e um espaço. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">1. Item<br>    1. Subitem<br>2. Item</code></pre> aparece como:<br><br><ol class="markdown"><li>Item<ol class="markdown"><li>Subitem</li></ol></li><li>Item</li></ol>',
	'HELP_MARKDOWN_TASK_LIST_QUESTION' => 'Como criar uma lista de tarefas?',
	'HELP_MARKDOWN_TASK_LIST_ANSWER' => 'Comece cada item com <code>*</code>, <code>-</code> ou <code>+</code>, seguido de um espaço. Use <code>[x]</code> para um item concluído e <code>[ ]</code> para um item pendente. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">- [x] Feito<br>    - [x] Subitem feito<br>- [ ] Pendente</code></pre> aparece como:<br><br><ul class="markdown"><li><input type="checkbox" checked disabled> Feito<ul class="markdown"><li><input type="checkbox" checked disabled> Subitem feito</li></ul></li><li><input type="checkbox" disabled> Pendente</li></ul>',

	'HELP_MARKDOWN_BLOCK_LINK' => 'Links',
	'HELP_MARKDOWN_LINK_QUESTION' => 'Como criar um link?',
	'HELP_MARKDOWN_LINK_ANSWER' => 'Coloque o texto do link entre colchetes e o endereço entre parênteses. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">[Texto do link](https://example.org)</code></pre> aparece como:<br><br><a href="https://example.org">Texto do link</a>',

	'HELP_MARKDOWN_BLOCK_IMAGE' => 'Imagens',
	'HELP_MARKDOWN_IMAGE_QUESTION' => 'Como inserir uma imagem?',
	'HELP_MARKDOWN_IMAGE_ANSWER' => 'Adicione <code>!</code> antes de um texto alternativo entre colchetes e coloque o endereço da imagem entre parênteses. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">![phpBB](https://www.phpbb.com/assets/images/images/logos/blue/160x52.png)</code></pre> aparece como:<br><br><img src="https://www.phpbb.com/assets/images/images/logos/blue/160x52.png" alt="phpBB">',

	'HELP_MARKDOWN_BLOCK_EXTRA' => 'Outros recursos',
	'HELP_MARKDOWN_HORIZONTAL_RULE_QUESTION' => 'Como criar uma linha horizontal?',
	'HELP_MARKDOWN_HORIZONTAL_RULE_ANSWER' => 'Escreva pelo menos três sinais <code>*</code>, <code>-</code> ou <code>_</code>, com ou sem espaços entre eles. Por exemplo:<pre class="markdown-code"><code class="markdown" data-lang="markdown">***<br>* * *<br>---<br>- - -<br>___<br>_ _ _</code></pre> aparece como:<br><br><hr>',
]);
