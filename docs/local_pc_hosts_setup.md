# Faster, more reliable access to GG Pickup

**Why:** This small change makes the apps load faster on your office computer and helps them keep working when the office internet is slow or having problems.

## On a Windows PC

1. Click the **Start** button, type `Notepad`
2. **Right-click** Notepad in the search results, choose **Run as administrator**
3. When Windows asks *"Do you want to allow this app to make changes?"*, click **Yes**

   [SCREENSHOT: notepad-as-admin]

4. In Notepad, click **File → Open**
5. Copy and paste this into the **File name** box: `C:\Windows\System32\drivers\etc\hosts`
6. Change the dropdown next to **File name** from **Text Documents** to **All Files**

   [SCREENSHOT: file-open-all-files]

7. Click **hosts** in the file list, then click **Open**
8. Scroll all the way to the bottom of the file
9. Add this line exactly (copy and paste it):

   ```
   192.168.1.121  gg.colorfashiondnf.com  shipping-web.colorfashiondnf.com
   ```

10. Click **File → Save** (do **not** use Save As)

    [SCREENSHOT: hosts-file-edited]

11. Close Notepad

## On a Mac

1. Press **Cmd + Space**, type **Terminal**, press **Enter**
2. Type this command and press **Enter**:

   ```
   sudo nano /etc/hosts
   ```

3. Type your Mac password when asked (you won't see the password as you type — that's normal)
4. Use the **down arrow** key to scroll to the bottom
5. Add the same line (paste with **Cmd + V**):

   ```
   192.168.1.121  gg.colorfashiondnf.com  shipping-web.colorfashiondnf.com
   ```

6. Press **Ctrl + O**, then **Enter** to save
7. Press **Ctrl + X** to quit

## Check it worked

1. Open **Command Prompt** (Windows) or **Terminal** (Mac)
2. Type: `ping gg.colorfashiondnf.com`
3. You should see **Reply from 192.168.1.121**
4. If yes, you're done. Close the window.

## If something doesn't work

Don't keep trying. Take a screenshot of what you see and message Daniel. He'll fix it.
