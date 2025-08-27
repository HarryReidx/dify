$(function(){
    // 初始化题目
    initializeQuestions();

    // 更新进度条
    updateProgress();

    function initializeQuestions() {
        var questionNumber = 1;

        // 处理所有题目容器，按DOM顺序
        $('.question-block').each(function() {
            var $this = $(this);

            // 添加必要的类
            $this.addClass('question-card question-row');

            // 添加题目编号
            if (!$this.find('.question-number').length) {
                $this.prepend('<div class="question-number">' + questionNumber + '</div>');
                questionNumber++;
            }

            // 处理选项列表
            var $optionList = $this.find('.option-list');
            if ($optionList.length > 0) {
                $optionList.find('li').each(function() {
                    var $li = $(this);
                    if (!$li.hasClass('option-item')) {
                        $li.addClass('option-item');
                    }

                    var $input = $li.find('input');
                    var $label = $li.find('label');

                    if ($input.length > 0 && $label.length > 0) {
                        // 确保label和input关联
                        var inputId = $input.attr('id');
                        if (!inputId) {
                            inputId = 'option_' + Math.random().toString(36).substr(2, 9);
                            $input.attr('id', inputId);
                        }
                        $label.attr('for', inputId);
                    }
                });

                // 检测题目类型并设置相应的类
                var hasRadio = $optionList.find('input[type="radio"]').length > 0;
                var hasCheckbox = $optionList.find('input[type="checkbox"]').length > 0;
                var hasText = $optionList.find('input[type="text"]').length > 0;

                if (hasRadio) {
                    $this.addClass('radio-list');
                    // 确保单选题有正确的name属性
                    var questionId = $this.data('question-id') || 'radio-question-' + questionNumber;
                    $optionList.find('input[type="radio"]').attr('name', questionId);
                } else if (hasCheckbox) {
                    $this.addClass('checklist');
                } else if (hasText) {
                    $this.addClass('textbox');
                    $optionList.find('input[type="text"]').addClass('text-input');
                }
            }
        });

        // 更新总题目数
        var totalQuestions = $('.question-row').length;
        $('#total-count').text(totalQuestions);
    }

    function updateProgress() {
        var totalQuestions = $('.question-row').length;
        var answeredQuestions = 0;

        $('.question-row').each(function() {
            var $this = $(this);
            var hasAnswer = false;

            if ($this.hasClass('radio-list')) {
                hasAnswer = $this.find('input[type="radio"]:checked').length > 0;
            } else if ($this.hasClass('checklist')) {
                hasAnswer = $this.find('input[type="checkbox"]:checked').length > 0;
            } else if ($this.hasClass('textbox')) {
                hasAnswer = $this.find('input[type="text"]').val().trim() !== '';
            }

            if (hasAnswer) {
                answeredQuestions++;
            }
        });

        var progress = totalQuestions > 0 ? (answeredQuestions / totalQuestions) * 100 : 0;
        $('#progress-fill').css('width', progress + '%');
    }

    function checkQuestion() {
        resetQuestions(true);
        var questions = $('.question-row');
        var total_questions = questions.length;
        var correct = 0;

        questions.each(function(i, el) {
            var $this = $(this);
            var isCorrect = false;
            var isPartial = false;

            // 单选题（包括判断题）
            if ($this.hasClass('radio-list') || $this.hasClass('radio-question')) {
                var $correctOption = $this.find('input[type="radio"][data-content="1"]');
                var $selectedOption = $this.find('input[type="radio"]:checked');

                if ($selectedOption.length > 0 && $selectedOption.data('content') == '1') {
                    correct += 1;
                    isCorrect = true;
                } else {
                    // 标记错误选项
                    if ($selectedOption.length > 0) {
                        $selectedOption.closest('.option-item').addClass('option-incorrect');
                    }
                    // 显示正确答案
                    $correctOption.closest('.option-item').addClass('option-correct-highlight');
                }
            }

            // 文本题
            else if ($this.hasClass('textbox')) {
                var $textbox = $this.find('input[type="text"]');
                var correct_text = String($textbox.data("content")).trim().split("").reverse().join("");
                var user_answer = String($textbox.val()).trim();

                if (user_answer.toLowerCase() == correct_text.toLowerCase()) {
                    correct += 1;
                    isCorrect = true;
                    $textbox.closest('.option-item').addClass('option-correct');
                } else {
                    $textbox.closest('.option-item').addClass('option-incorrect');
                    // 显示正确答案
                    if (!$this.find('.correct-answer').length) {
                        $this.append('<div class="correct-answer"><i class="fas fa-info-circle"></i> 正确答案: ' + correct_text + '</div>');
                    }
                }
            }

            // 多选题
            else if ($this.hasClass('checklist')) {
                var total_corrects = $this.find('input[type="checkbox"][data-content="1"]').length;
                var total_incorrects = $this.find('input[type="checkbox"][data-content="0"]').length;
                var correct_selected = $this.find('input[type="checkbox"][data-content="1"]:checked').length;
                var incorrect_selected = $this.find('input[type="checkbox"][data-content="0"]:checked').length;

                // 标记选项状态
                $this.find('input[type="checkbox"]').each(function() {
                    var $checkbox = $(this);
                    var $optionItem = $checkbox.closest('.option-item');
                    var isCorrectOption = $checkbox.data('content') == '1';
                    var isSelected = $checkbox.is(':checked');

                    if (isSelected) {
                        if (isCorrectOption) {
                            $optionItem.addClass('option-correct');
                        } else {
                            $optionItem.addClass('option-incorrect');
                        }
                    } else if (isCorrectOption) {
                        $optionItem.addClass('option-missed');
                    }
                });

                var qc = 0;
                if (total_corrects > 0) {
                    qc = (correct_selected / total_corrects) - (incorrect_selected / total_corrects);
                    if (qc < 0) qc = 0;
                }

                correct += qc;

                if (qc === 1) {
                    isCorrect = true;
                } else if (qc > 0) {
                    isPartial = true;
                }
            }

            // 添加题目级别的视觉反馈
            if (isCorrect) {
                $this.addClass('question-correct');
            } else if (isPartial) {
                $this.addClass('question-partial');
            } else {
                $this.addClass('question-incorrect');
            }
        });

        showScore(correct, total_questions);
    }

    function showScore(correct, total) {
        var score = Math.round((correct / total) * 100);
        $('#score-number').text(score + '%');
        $('#correct-count').text(correct);
        $('#total-count').text(total);

        // 根据分数设置样式
        var scoreCard = $('#score-display');
        scoreCard.removeClass('show danger warning');

        if (score >= 80) {
            scoreCard.addClass('show');
            $('#score-text').html('<i class="fas fa-trophy"></i> 优秀！');
        } else if (score >= 60) {
            scoreCard.addClass('show warning');
            $('#score-text').html('<i class="fas fa-medal"></i> 良好！');
        } else {
            scoreCard.addClass('show danger');
            $('#score-text').html('<i class="fas fa-times-circle"></i> 需要努力！');
        }

        // 滚动到分数显示区域
        $('html, body').animate({
            scrollTop: scoreCard.offset().top - 100
        }, 500);
    }

    function resetQuestions(keep) {
        $('.question-row').removeClass('question-correct question-incorrect question-partial');
        $('.option-item').removeClass('option-correct option-incorrect option-correct-highlight option-missed');
        $('.correct-answer').remove();
        $('#score-display').removeClass('show danger warning');
        $('#progress-fill').css('width', '0%');

        if (keep === true) {
            return;
        }

        $('.question-row').find('input[type="text"]').val('');
        $('.question-row').find('input[type="radio"], input[type="checkbox"]').prop('checked', false);
        updateProgress();
    }

    function updateProgress() {
        var totalQuestions = $('.question-row').length;
        var answeredQuestions = 0;

        $('.question-row').each(function() {
            var $this = $(this);
            var hasAnswer = false;

            // 检查单选题和多选题
            if ($this.find('input[type="radio"]:checked, input[type="checkbox"]:checked').length > 0) {
                hasAnswer = true;
            }

            // 检查填空题
            if ($this.find('input[type="text"]').filter(function() {
                return $(this).val().trim() !== '';
            }).length > 0) {
                hasAnswer = true;
            }

            if (hasAnswer) {
                answeredQuestions++;
            }
        });

        var progress = totalQuestions > 0 ? (answeredQuestions / totalQuestions) * 100 : 0;
        $('#progress-fill').css('width', progress + '%');
    }

    // 事件绑定
    $('#check-questions').on('click', checkQuestion);
    $('#reset-questions').on('click', resetQuestions);

    // 监听输入变化以更新进度条
    $(document).on('change', 'input[type="radio"], input[type="checkbox"]', updateProgress);
    $(document).on('input', 'input[type="text"]', updateProgress);

    // 点击选项项时也选中对应的input
    $(document).on('click', '.option-item', function(e) {
        if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'LABEL') {
            var $input = $(this).find('input');
            if ($input.attr('type') === 'radio') {
                $input.prop('checked', true);
            } else if ($input.attr('type') === 'checkbox') {
                $input.prop('checked', !$input.prop('checked'));
            }
            updateProgress();
        }
    });
});
