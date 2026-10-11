/**
 * Interface strings.
 *
 * The patient never has to read English, so every label, button and status
 * message exists in both languages. Only the clinician's original document
 * text stays in English, and it stays visible on purpose.
 */

export const STRINGS = {
  en: {
    appName: 'PlainTalk',
    tagline: 'Understand your health papers',

    pickLanguage: 'Choose your language',
    pickLanguageHelp: 'Everything after this will be in the language you pick.',
    continue: 'Continue',

    uploadTitle: 'Add your health paper',
    uploadHelp: 'A discharge sheet, lab result, or medicine guide. Type it in, or paste it if you have it on a computer.',
    pasteLabel: 'Type or paste what your paper says',
    pastePlaceholder: 'Type or paste your health paper here',
    usePasted: 'Read my paper',
    orFile: 'or',
    chooseFile: 'Pick a file from this device',
    chooseFileHelp: 'Only if your paper is already saved on this device.',
    uploading: 'Reading your paper…',
    translatingDoc: 'Translating…',
    translateAll: 'Translate the whole paper',
    translateAllHelp: 'Takes about a minute. You can also translate one part at a time.',
    stopTranslating: 'Stop',

    document: 'Your paper',
    questions: 'Questions',
    forDoctor: 'Questions for my doctor',

    simplify: 'Explain more simply',
    simplifying: 'Making it simpler…',
    showVietnamese: 'Show in Vietnamese',
    translating: 'Translating…',
    original: 'Original from your doctor',
    level: 'Level',
    reading: 'Reading level',
    checked: 'Checked: medicine names, doses, times, dates',
    ladderDone: 'This is the simplest version',
    gateBlocked: 'A simpler version was not safe to show, so the last checked version is kept.',

    askPlaceholder: 'Ask about your paper',
    send: 'Ask',
    thinking: 'Looking in your paper…',
    source: 'From your paper',

    refusalTitle: 'Question for your doctor',
    abstainTitle: 'Not in your paper',
    emergencyTitle: 'This may be an emergency',
    savedForDoctor: 'Added to the list for your doctor.',

    handoffTitle: 'Questions for my doctor',
    handoffEmpty: 'No questions yet. Anything I cannot answer will appear here.',
    handoffHelp: 'Print this page and bring it to your appointment.',
    print: 'Print',
    back: 'Back',

    startOver: 'Start over',
    errorTitle: 'Something went wrong',
    retry: 'Try again',
  },

  vi: {
    appName: 'PlainTalk',
    tagline: 'Hiểu thêm về giấy tờ sức khỏe',

    pickLanguage: 'Chọn ngôn ngữ',
    pickLanguageHelp: 'Sau bước này, mọi thứ sẽ hiển thị bằng ngôn ngữ đã chọn.',
    continue: 'Tiếp tục',

    uploadTitle: 'Thêm giấy tờ sức khỏe',
    uploadHelp: 'Giấy xuất viện, kết quả xét nghiệm, hoặc hướng dẫn dùng thuốc. Có thể gõ vào, hoặc dán nếu đã có sẵn trong máy.',
    pasteLabel: 'Gõ hoặc dán nội dung trên giấy',
    pastePlaceholder: 'Gõ hoặc dán nội dung giấy tờ vào đây',
    usePasted: 'Đọc giấy của tôi',
    orFile: 'hoặc',
    chooseFile: 'Lấy từ trong máy này',
    chooseFileHelp: 'Chỉ dùng nếu giấy tờ đã được lưu sẵn trong máy.',
    uploading: 'Đang đọc giấy tờ…',
    translatingDoc: 'Đang dịch…',
    translateAll: 'Dịch toàn bộ giấy tờ',
    translateAllHelp: 'Mất khoảng một phút. Cũng có thể dịch từng phần một.',
    stopTranslating: 'Dừng',

    document: 'Giấy tờ sức khỏe',
    questions: 'Câu hỏi',
    forDoctor: 'Câu hỏi cho bác sĩ',

    simplify: 'Giải thích đơn giản hơn',
    simplifying: 'Đang làm cho dễ hiểu hơn…',
    showVietnamese: 'Xem bằng tiếng Việt',
    translating: 'Đang dịch…',
    original: 'Bản gốc từ bác sĩ',
    level: 'Mức',
    reading: 'Trình độ đọc',
    checked: 'Đã kiểm tra: tên thuốc, liều lượng, số lần, ngày tháng',
    ladderDone: 'Đây là bản đơn giản nhất',
    gateBlocked: 'Bản đơn giản hơn chưa an toàn để hiển thị, nên giữ lại bản đã kiểm tra.',

    askPlaceholder: 'Hỏi về giấy tờ',
    send: 'Hỏi',
    thinking: 'Đang tìm trong giấy tờ…',
    source: 'Trích từ giấy tờ',

    refusalTitle: 'Câu hỏi cho bác sĩ',
    abstainTitle: 'Không có trong giấy tờ',
    emergencyTitle: 'Đây có thể là trường hợp khẩn cấp',
    savedForDoctor: 'Đã thêm vào danh sách cho bác sĩ.',

    handoffTitle: 'Câu hỏi cho bác sĩ',
    handoffEmpty: 'Chưa có câu hỏi nào. Những câu tôi không trả lời được sẽ hiện ở đây.',
    handoffHelp: 'Hãy in trang này và mang theo khi đi khám.',
    print: 'Print',
    back: 'Quay lại',

    startOver: 'Bắt đầu lại',
    errorTitle: 'Có lỗi xảy ra',
    retry: 'Thử lại',
  },
}

export const useStrings = (lang) => STRINGS[lang] || STRINGS.en
