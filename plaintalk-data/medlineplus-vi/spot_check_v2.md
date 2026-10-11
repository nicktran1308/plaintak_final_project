# MedlinePlus VI - spot check v2 (LaBSE-filtered)

Sampled from `pairs_scored.jsonl` (seed 7). `cos` is LaBSE cosine similarity
between the EN and VI fields. Exemplar cutoff is cos >= 0.72, plus a list-number
consistency check.

- Group A: 10 random from the final exemplar set (population 2783)
- Group B: 5 just ABOVE the cutoff, cos 0.72-0.78 (population 315) - where false keeps hide
- Group C: 5 just BELOW the cutoff, cos 0.62-0.72 (population 225) - where false drops hide

Groups B and C test the threshold placement. If B is clean and C is genuinely
bad, 0.72 sits correctly. If C contains good pairs, the cutoff is too high.

---

## Group A - accepted exemplars

### 1. Your Recovery After Cesarean Birth

- topic: Cesarean Delivery
- cos: 0.876 ratio: 1.11

EN:

> Sit up for a couple of minutes before you start to walk. If you feel light headed or dizzy while in the bathroom, pull the emergency call light on the bathroom wall for help.

VI:

> Ngồi dậy vài phút trước khi quý vị bắt đầu đi lại. Nếu quý vị thấy choáng váng hoặc chóng mặt khi đang trong phòng vệ sinh, hãy bấm đèn gọi cấp cứu trên tường của phòng vệ sinh để được giúp đỡ.

### 2. What You Can Do to Sleep Better

- topic: Sleep Disorders
- cos: 0.748 ratio: 1.23

EN:

> Develop a bedtime routine.

VI:

> Xây dựng thói quen ngủ đúng giờ.

### 3. High Blood Pressure (Hypertension)

- topic: High Blood Pressure
- cos: 0.856 ratio: 1.32

EN:

> Blood pressure is often checked by putting a wide band called a cuff around your upper arm. Air is pumped into the cuff. Your blood pressure is measured as the air is let out of the cuff.

VI:

> Người ta thường đo huyết áp bằng cách cuộn một dải băng rộng gọi là băng đo huyết áp xung quanh phần cánh tay phía trên. Không khí được bơm vào trong băng đo huyết áp. Máy sẽ đo huyết áp của quý vị khi không khí xì ra khỏi chiếc băng đo huyết áp.

### 4. Getting Your Skin Ready for Surgery

- topic: Surgery
- cos: 0.932 ratio: 0.88

EN:

> 1. Use the washcloth to wash your whole body from the neck down. Keep adding more CHG and continue to wash for 5 minutes.

VI:

> 1. Sử dụng khăn lau để lau toàn bộ cơ thể từ cổ trở xuống. Tiếp tục thêm CHG và tiếp tục lau trong 5 phút.

### 5. Head Lice

- topic: Head Lice
- cos: 0.984 ratio: 0.97

EN:

> How to Use Piperonyl Butoxide

VI:

> Cách dùng Piperonyl Butoxide

### 6. Breastfeeding Problems

- topic: Breastfeeding
- cos: 0.774 ratio: 1.08

EN:

> If latching on still painful, talk to a lactation specialist.

VI:

> Nếu vú vẫn đau khi bám, hãy cho chuyên gia tư vấn về sữ̃a mẹ biết.

### 7. Heart Attack

- topic: Heart Attack
- cos: 0.863 ratio: 1.03

EN:

> Ask about getting into a cardiac rehab program to help you gain strength and get more active.

VI:

> Hỏi về việc tham gia chương trình hồi phục tim để giúp quý vị lấy lại sức khỏe và năng động hơn.

### 8. Crutch Walking

- topic: Mobility Aids
- cos: 0.770 ratio: 1.61

EN:

> 1. Reach back for the chair with your other hand.

VI:

> 1. Dùng tay còn lại với ra ghế ở phía sau. 4. Từ từ ngồi xuống ghế, gập ở hông.

### 9. Caring for Your Baby

- topic: Infant and Newborn Care
- cos: 0.876 ratio: 0.98

EN:

> 1. Gently insert the tip into the nose and then slowly release the bulb. Do not force the tip high into the nose.

VI:

> 1. Nhẹ nhàng đưa đầu bầu hút vào trong mũi và sau đó từ từ thả bầu. Không cố đưa đầu bầu hút vào sâu trong mũi.

### 10. Cancer Chemotherapy

- topic: Cancer Chemotherapy
- cos: 0.930 ratio: 1.09

EN:

> Chemotherapy, also called chemo, is medicines used to treat cancer. These medicines destroy cancer cells, keep them from growing and spreading, shrink the size of a tumor, or relieve cancer symptoms.

VI:

> Trị liệu hóa chất (chemotherapy), cũng được gọi là chemo, là thuốc dùng chữa trị ung thư. Những thuốc này phá hủy tế bào ung thư, ngăn chúng cho khỏi phát triển và lan tràn, làm nhỏ bướu hoặc giảm triệu chứng ung thư.

---

## Group B - just above cutoff (0.72-0.78)

### 1. Breastfeeding Problems

- topic: Breastfeeding
- cos: 0.770 ratio: 0.88

EN:

> Larger, heavier and tender breasts

VI:

> Vú lớn hơn, nặng hơn và dễ đau

### 2. Appendectomy

- topic: Appendicitis
- cos: 0.772 ratio: 1.01

EN:

> Your doctor will talk to you about your surgery and when you can expect to go home.

VI:

> Bác sĩ sẽ cho quý vị biết kết quả phẫu thuật và thời điểm quý vị có thể được về nhà.

### 3. Getting Started Breastfeeding Your Baby

- topic: Breastfeeding
- cos: 0.724 ratio: 1.00

EN:

> Getting Ready to Breastfeed

VI:

> Cách chuẩn bị cho trẻ bú vú

### 4. Your Recovery After Vaginal Birth

- topic: Childbirth
- cos: 0.773 ratio: 0.92

EN:

> Foul smelling vaginal discharge—a normal discharge smells like your menstrual period.

VI:

> Khí hư ở âm đạo có mùi hôi—khí hư bình thường có mùi tương tự mùi kinh nguyệt.

### 5. Crutch Walking

- topic: Mobility Aids
- cos: 0.743 ratio: 0.77

EN:

> Using Your Crutches Safely

VI:

> Sử dụng nạng An toàn

---

## Group C - just below cutoff (0.62-0.72), DROPPED

### 1. Caring for Your Baby

- topic: Infant and Newborn Care
- cos: 0.634 ratio: 1.57

EN:

> Sucking sounds

VI:

> Âm thanh mút chùn chụt

### 2. Pumping and Storing Breast Milk

- topic: Breastfeeding
- cos: 0.665 ratio: 1.00

EN:

> Massage breast toward nipple to express milk.

VI:

> Xoa bóp vú, từ từ hướng về núm vú để vắt sữa.

### 3. Kidney Failure

- topic: Kidney Failure
- cos: 0.681 ratio: 1.50

EN:

> The kidneys:

VI:

> Thận có chức năng:

### 4. Exercises to Strengthen Your Shoulder

- topic: Rehabilitation
- cos: 0.697 ratio: 1.69

GroEN:

> Lift your arm out to your side until it is parallel to the floor.

VI:

> Nâng tay lên ngang sườn cho đến khi song song với sàn. Giữ nguyên rồi hạ từ từ tay xuống. Thư giãn và lặp lại.

### 5. Facial Strengthening Exercises

- topic: Facial Injuries and Disorders
- cos: 0.627 ratio: 0.93

EN:

>  Tongue Blade

VI:

>  Que đè lưỡi
