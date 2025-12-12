/**
 * パレットの表示・非表示を切り替える
 */
function toggleThemePalette() {
    const palette = document.getElementById('themePalette');
    palette.classList.toggle('show');
}

/**
 * テーマを切り替えてブラウザのLocalStorageに保存する
 * @param {string} themeName - CSSのクラス名 ('theme-blue' など。デフォルトは空文字列)
 */
function changeTheme(themeName) {
    // 1. 既存のテーマクラスを全て除去
    document.body.classList.remove('theme-blue', 'theme-yellow', 'theme-purple', 'theme-green');
    
    // 2. 新しいテーマがあれば適用
    if (themeName) {
        document.body.classList.add(themeName);
    }

    // 3. ブラウザに保存
    localStorage.setItem('selected-theme', themeName);

    // 4. ボタンの強調表示を更新
    updateActiveDot(themeName);

    // 5. 色を選んだらパレットをにゅっと閉じる (少し遅延させて余韻を残す)
    setTimeout(() => {
        const palette = document.getElementById('themePalette');
        palette.classList.remove('show');
    }, 400);
}

/**
 * 選択中のドットを強調する
 */
function updateActiveDot(themeName) {
    const dots = document.querySelectorAll('.theme-dot');
    dots.forEach(dot => dot.classList.remove('active'));

    // 現在のテーマに対応するドットのセレクタを決定
    let selector = '.dot-pink'; // デフォルト (ピンク)
    if (themeName === 'theme-blue') selector = '.dot-blue';
    if (themeName === 'theme-yellow') selector = '.dot-yellow';
    if (themeName === 'theme-purple') selector = '.dot-purple';
    if (themeName === 'theme-green') selector = '.dot-green';

    // 該当するドットに active クラスを付与
    const activeDot = document.querySelector(selector);
    if (activeDot) activeDot.classList.add('active');
}

/**
 * ページ読み込み時の初期化処理
 */
document.addEventListener('DOMContentLoaded', () => {
    // 保存されたテーマがあれば読み込む
    const savedTheme = localStorage.getItem('selected-theme');
    if (savedTheme !== null) {
        changeTheme(savedTheme);
    } else {
        updateActiveDot('');
    }

    // パレットの外側をクリックしたら閉じる設定（ユーザー体験向上のため）
    document.addEventListener('click', (event) => {
        const palette = document.getElementById('themePalette');
        const paletteBtn = document.querySelector('[onclick="toggleThemePalette()"]');
        
        // クリックした要素がパレット内でも、🎨ボタンでもない場合、パレットを閉じる
        if (palette.classList.contains('show') && !palette.contains(event.target) && !paletteBtn.contains(event.target)) {
            palette.classList.remove('show');
        }
    });
});