from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import underthesea
import warnings
warnings.filterwarnings("ignore")

train_sentences = [
    # --- ADD ---
    "nhắc tôi họp nhóm",
    "nhắc tôi đi học lúc 8 giờ",
    "nhắc tôi có lịch sinh nhật",
    "thêm lịch sinh nhật",
    "đặt lịch họp với sếp",
    "tạo lịch đi ăn trưa ngày mai",
    "nhắc tôi ngày mai có lịch hẹn đi ăn tối lúc 19 giờ",
    "tôi muốn thêm sự kiện họp vào ngày mai",
    # --- DELETE ---
    "xóa lịch họp hôm nay",
    "bỏ sự kiện ngày mai",
    "hủy lịch sinh nhật",
    # --- SHOW ---
    "hiển thị lịch hôm nay",
    "xem các sự kiện ngày mai",
    "ngày mai tôi có lịch gì không",
    "cho tôi biết hôm nay có lịch gì",
    # --- UPDATE ---
    "cập nhật sự kiện họp nhóm",
]
train_labels = [
    "add_event",
    "add_event",
    "add_event",
    "add_event",
    "add_event",
    "add_event",
    "add_event",
    "add_event",
    "delete_event",
    "delete_event",
    "delete_event",
    "show_event",
    "show_event",
    "show_event",
    "show_event",
    "update_event",
]

vectorizer = TfidfVectorizer(tokenizer=underthesea.word_tokenize)
X_train = vectorizer.fit_transform(train_sentences)
clf = MultinomialNB()
clf.fit(X_train, train_labels)

def predict_intent(text: str):
    X = vectorizer.transform([text])
    return clf.predict(X)[0]
